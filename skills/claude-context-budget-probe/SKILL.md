---
name: claude-context-budget-probe
description: "Measure what a new Claude Code session loads before the first message (tools, skills, CLAUDE.md, hooks) via a probe session, and prove a setup change worked. Use for \"скільки займає контекст\", \"переміряй базу контексту\", \"чи спрацювало урізання\", \"що ще велике в контексті\"."
---

# Context budget probe

Measures the first API request of a fresh session and splits it by component. The baseline
history and findings live in `~/work/claude-code-adaptive-orchestration/docs/context-budget.md`
(88k on 2026-11-11 → 44,013 on 2026-11-12); append new results there and push.

## Procedure

1. **Start a probe session yourself** — never ask the owner to open one. `start_session`,
   `initiation: user_asked`, `context: fresh`, `use_worktree: false`, `wake_when_done: true`,
   prompt: `Reply with the single word ok. Do not call any tools.` plus a unique phrase in
   `background` (e.g. "Measurement probe: the parent session reads…") to find its transcript.
   A headless `claude -p` run is not comparable: it lacks the desktop app's tools and prompt.
2. When it reports `ok`, measure:
   ```bash
   python3 ~/.claude/skills/claude-context-budget-probe/scripts/measure.py --find "Measurement probe: the parent" --compare <previous probe .jsonl>
   ```
   It prints the exact total (`input + cache_creation + cache_read` of the first usage),
   per-component chars and proportional tokens, largest tools, skill-listing stats, and with
   `--compare` the tools removed/added and skill entries that grew or shrank.
3. Change one thing, probe again, compare. Archive the probe sessions after the owner agrees.

## What actually moves the number (verified 2026-11-12, CLI 2.1.321)

- `permissions.deny: ["ToolName"]` removes **CLI** tools (`Workflow` worked). It does **not**
  remove tools the desktop app injects (`mcp__ccd_*`, `mcp__visualize__*`, `mcp__terminal__*`),
  not even a server-level `mcp__visualize` rule, and the app has no setting for them.
  Always confirm a deny in the probe's tool list instead of trusting the config.
- The skill listing has a fixed budget (`skillListingBudgetFraction`, default 1% of the
  window). Shortening descriptions alone does nothing: freed space is refilled with plugin
  skill descriptions that were name-only before. `skillListingMaxDescChars` (default 1536)
  caps every entry and is what shrinks the listing; 300 is set now, so keep personal
  descriptions ≤ ~290 chars with the trigger phrases first, or they get cut mid-sentence.
- `skillOverrides` `name-only` / `off` works for personal and bundled skills, not plugin ones.
- Fixed by the app: system prompt (~31k chars), `wrap_up` / `update_plan` and other app tools.
- The UserPromptSubmit task-contract hook repeats on every user message (~1.3k chars).

Back up before editing settings or skills: `~/.claude/self-improve/backups/<date>-<tag>/`
with paths relative to `~`. Push changes to the public setup repo.
