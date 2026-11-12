# SPEC: a Claude Code setup that builds and maintains itself

Owner decisions, 2026-11-12 (AskUserQuestion, verbatim choices):

| Question | Decision |
|---|---|
| What may Claude change alone | **Creates and edits itself, deletes only with a yes.** New skills, edits to skills, project `CLAUDE.md`, agents and hooks: done alone, with a backup and a report. Deleting a skill or rule, and any edit to the global `~/.claude/CLAUDE.md`: proposed in one weekly list, applied after the owner's yes. Existing rules stay. |
| When it learns | **After each session + weekly.** At the end of a meaningful task the session records lessons (owner corrections, repeated procedures). A weekly task reviews all sessions, creates/cleans skills and rules, and checks Anthropic best practice. |
| Where it reports and asks | **A weekly session in the app**: a report in Ukrainian and up to 4 questions as buttons (AskUserQuestion). |
| Scope | **Everything: code + assistant.** Global skills and rules, plus project skills in each folder (every code workspace and the personal assistant folder), each in its own folder. |

The owner does not want to think about configuration. Claude learns how the owner talks and what they want, and adapts the setup around them.

## Current setup (read these first)

- Global rules `~/.claude/CLAUDE.md`; settings `~/.claude/settings.json` (bypassPermissions, one UserPromptSubmit hook `~/.claude/hooks/task-contract.py`, per-project override `.claude/task-contract.md`).
- Agents `~/.claude/agents/` (money-reviewer, reviewer, scout, verifier). Skills `~/.claude/skills/` (~45) and project skills under `<repo>/.claude/skills/`.
- Memory: auto memory per project (`~/.claude/projects/<key>/memory`, index `MEMORY.md`), claude-mem plugin, personal vault `~/assistant/vault`.
- Weekly scheduled task `memory-staleness-audit` (Mon 09:33) with skill `~/.claude/skills/memory-staleness-audit` (lint `scripts/memory_lint.py`).
- Public mirror: this repo (`byigorduvanov/claude-adaptive-orchestration`); every setup change is synced here, private data stripped (see memory note `feedback-sync-claude-setup-to-public-repo`).
- Owner rules that constrain this work: show global `CLAUDE.md` edits before applying; deleting the owner's files needs a yes; subagents set `model`/`effort` per the tiers; pathspec commits only.

## Part 1 — Best-practice audit (do first)

Compare the setup against Anthropic's current guidance and list gaps with sources. Read the sources now (Context7 / the docs site / anthropic.com engineering posts), never from memory: Claude Code best practices, memory and `CLAUDE.md` (size, imports, `.claude/rules/`), skills (description, progressive disclosure, scripts), subagents, hooks (all events available in the installed version, `claude --version`), settings/permissions, output styles, plugins, context management and compaction, headless/scheduled use.

Output `docs/best-practice-audit-2026-11.md`: one row per practice — what Anthropic recommends (link + date read), what we do (file:line), verdict (follow / gap / deliberately different + why), the fix. Apply the gaps that the autonomy rule allows; global `CLAUDE.md` gaps go to the owner as one shown diff.

## Part 2 — Self-improvement loop

1. **Signals, cheap and automatic.**
   - A `PreToolUse` hook on the `Skill` tool appends `{date, skill, cwd}` to `~/.claude/self-improve/skill-usage.jsonl` (usage → what is dead).
   - A `SessionEnd` (or `Stop`) hook appends `{date, cwd, transcript_path}` to `~/.claude/self-improve/sessions.jsonl` (the weekly run's reading list). No model call inside hooks; each hook < 50 ms, exits 0 on any error, has a test in `tests/`.
2. **In-session rule** (global `CLAUDE.md`, shown to the owner first): at the end of a meaningful task, when the owner corrected the approach or a non-trivial procedure repeated, update or create the skill/memory in that turn (extends the existing "Skill Creator" section; do not duplicate it).
3. **Weekly task `setup-self-improve`** (scheduled, after the memory audit, e.g. Mon 10:03), skill `~/.claude/skills/setup-self-improve/`:
   - read the week's `sessions.jsonl` transcripts in batches (sonnet/medium readers, ≤25-line summaries each): owner corrections, repeated multi-step procedures, questions the owner had to answer twice, rules that were ignored or got in the way;
   - create/update skills with `skill-creator` (project scope for repo knowledge, personal for habits); update an overlapping skill instead of adding one;
   - flag skills unused for 30+ days (from `skill-usage.jsonl`) and rules that never fired or conflict, as deletion proposals;
   - re-check Anthropic docs for changes since the last run (record the date read);
   - back up every file before editing (`~/.claude/self-improve/backups/<date>/`), sync the public repo, re-run `tests/` and the memory lint;
   - report in Ukrainian in the app session: what changed (file → why, with the transcript evidence), deletion/global-rule proposals as up to 4 AskUserQuestion buttons, what it could not decide.
4. **Guards.** Never weaken a safety rule (money paths, payments, deletion, force-push, retired hosts) by self-edit; such changes are always proposals. A self-created rule cites the session(s) it came from. Max 5 new skills per run. Every change is reversible from the backup.

## Done when

- `docs/best-practice-audit-2026-11.md` exists with sources and dates; allowed gaps applied; the global `CLAUDE.md` diff shown to the owner.
- Both hooks installed, `python3 tests/…` passes for them (including a malformed-input case), and a real session leaves a line in each jsonl.
- `setup-self-improve` skill + scheduled task exist; one manual run (`run_scheduled_task`) on this week's sessions produced a report with at least one concrete change or a stated "nothing found" with evidence, and its questions appeared as buttons.
- Public repo synced, private-name scan clean, `git ls-remote` matches.
