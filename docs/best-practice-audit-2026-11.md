# Best-practice audit, 2026-11

The setup compared with Anthropic's current Claude Code guidance. Claude Code 2.1.322. Every source was read live on **2026-11-12** (WebFetch of the pages below, none failed). The skills and sub-agents pages were read to about 100k of their 117–119k characters; the hooks page was read whole, in chunks.

Verdicts:
- **follow** — we already do what Anthropic recommends.
- **gap → fixed** — it was missing and was applied on 2026-11-12, with a backup in `~/.claude/self-improve/backups/2026-11-12/`.
- **gap → proposal** — missing, but it needs the owner's yes (global `CLAUDE.md`, deletion, a new prompt).
- **gap → weekly** — missing; left for the `setup-self-improve` weekly run.
- **deliberately different** — we chose otherwise, and the reason is given.

Sources (short names used in the table):

| Key | URL |
|---|---|
| BP | https://code.claude.com/docs/en/best-practices (the old anthropic.com/engineering/claude-code-best-practices now redirects here) |
| MEM | https://code.claude.com/docs/en/memory |
| SK | https://code.claude.com/docs/en/skills |
| SKA | https://platform.claude.com/docs/en/agents-and-tools/agent-skills/best-practices |
| SUB | https://code.claude.com/docs/en/sub-agents |
| HK | https://code.claude.com/docs/en/hooks |
| SET | https://code.claude.com/docs/en/settings |
| PRM | https://code.claude.com/docs/en/permissions · https://code.claude.com/docs/en/permission-modes |
| SBX | https://code.claude.com/docs/en/sandboxing |
| CST | https://code.claude.com/docs/en/costs |
| CTX | https://code.claude.com/docs/en/context-window |
| HL | https://code.claude.com/docs/en/headless |
| SCH | https://code.claude.com/docs/en/scheduled-tasks · https://code.claude.com/docs/en/desktop-scheduled-tasks |
| OS | https://code.claude.com/docs/en/output-styles |
| PL | https://code.claude.com/docs/en/plugins |
| CE | https://www.anthropic.com/engineering/effective-context-engineering-for-ai-agents |
| MA | https://www.anthropic.com/engineering/multi-agent-research-system |

Raw notes, with one quoted line per recommendation (about 105 rows), and a copy of this audit with real file names are kept outside the repo; the rows below are the ones that change something or confirm a choice.

## Memory and CLAUDE.md

| # | Anthropic recommends | We do | Verdict | Fix |
|---|---|---|---|---|
| 1 | "Target under 200 lines per CLAUDE.md file" (MEM, CST) | Global `~/.claude/CLAUDE.md`: 67 lines | follow | — |
| 2 | Same limit for project files | Two trading-service repos: 228 and 226 lines; their worktree copies up to 504 | gap → weekly | Trimming these risks dropping operational preconditions, so it waits for a careful per-repo pass: move procedures into skills and keep the warnings verbatim |
| 3 | Only what Claude cannot derive from code: verify commands, misleading spots, decisions, "anything you've had to correct twice" (BP) | Global rules are about behaviour and proof, not architecture | follow | The new in-session rule (#30) turns "corrected twice" into a lesson written that same turn |
| 4 | No IMPORTANT / ALL CAPS emphasis, which makes rules over-apply (BP) | `CLAUDE.md:53` "ONE message", `:62` "NOT proof"; bold on the one ask-first exception (`:46`) | deliberately different | The two capitals guard the two failures that cost the most (serial tool calls, a false "done"); the bold marks the single safety exception. Re-check on the next model, as `CLAUDE.md` Orchestration says |
| 5 | A rule that must hold every time belongs in a hook or deny rule; CLAUDE.md is for guidelines (BP, MEM) | Force-push and deletion "ask first" live only in `CLAUDE.md:46` | gap → proposal | One question for the owner: add `ask` rules for `git push --force*` / `-f*` (ask rules still prompt in bypass mode, PRM). An earlier `PreToolUse` force-push guard was removed on purpose (README "Removed"), so this is the owner's call, not applied alone |
| 6 | `.claude/rules/*.md` with `paths:` for rules that apply to one part of the tree (MEM) | No rules directories; the trading-workspace operations block sits in the global file (`CLAUDE.md:42-47`) | deliberately different | That block also governs skills written anywhere (no gates, keep preconditions), and moving it needs a global edit. Revisit if the global file passes 120 lines |
| 7 | MEMORY.md loads only the first 200 lines / 25 KB (MEM) | `memory_lint.py` checks `index-size` weekly; the main project's `MEMORY.md` is 33 lines | follow | — |
| 8 | Contradictory instructions are picked arbitrarily; audit with `/doctor prompt-audit` (MEM) | Not run | gap → weekly | Added to the `setup-self-improve` checklist: look for rules that conflict or never fired |

## Skills

| # | Anthropic recommends | We do | Verdict | Fix |
|---|---|---|---|---|
| 9 | SKILL.md under 500 lines; the body is a recurring token cost (SK, SKA) | A listing-backtest skill was 543 lines; all others ≤ 485 | gap → fixed | The order-book section moved word for word to `references/orderbook-pump-forecast.md`, with a pointer; SKILL.md is now 477 lines |
| 10 | Reference files more than 100 lines long get a table of contents (SKA) | 13 reference files over 100 lines had none | gap → fixed | Contents lines added to 8 global reference files that have ≥3 sections. The vendored `skill-creator` and project repos were left alone; the other 5 have fewer than 3 sections |
| 11 | description + `when_to_use` are cut at 1,536 characters in the listing; key use case first (SK). The API limit is 1,024 (SKA) | Global skills ≤ 892 characters; 4 skills in one project run 1,131–1,386 | follow (Claude Code) | Under the 1,536 Claude Code cut. Above the API limit only matters if they are uploaded to the API |
| 12 | Third person, what + when, specific trigger terms (SKA) | Descriptions say what + "Use for …" with the owner's real phrases in Ukrainian and English | follow | — |
| 13 | Gerund names (`processing-pdfs`) (SKA) | Domain-noun names (`<workspace>-trade-postmortem`) | deliberately different | The names group by domain in the listing; renaming breaks the owner's `/name` habits and memory links |
| 14 | `disable-model-invocation: true` for skills with side effects (SK) | Not set on the skills that flatten an exchange account or open a live test position | deliberately different | The owner asks in plain words ("продай всі монети на біржі") and wants the skill to load on that; user-only invocation would hide the skill and its warnings exactly when needed. The safety lives in the skill's preconditions |
| 15 | `skillOverrides` (`on` / `name-only` / `user-invocable-only` / `off`) to cut listing cost (SK) | 4 skills `off`, 5 `name-only` (`settings.json`) | follow | The weekly run proposes more from usage data (#24) |
| 16 | At least 3 evals before writing a skill at length; test on Haiku, Sonnet, Opus (SKA) | `money-reviewer` has evals; most skills do not | deliberately different | Most skills are written from a procedure that just succeeded on real work, which is the eval. The money reviewer, where a miss costs money, has an eval set |
| 17 | Scripts are executed, not loaded; give bundled script paths with `${CLAUDE_SKILL_DIR}` (SK) | Skills run scripts from `~/.claude/skills/<name>/scripts/…` with absolute paths | follow | Absolute paths also work when a scheduled task runs the script |

## Subagents

| # | Anthropic recommends | We do | Verdict | Fix |
|---|---|---|---|---|
| 18 | Subagents cost tokens; use them for parallel work, noisy output, an independent reviewer or restricted tools. "Protect your context" and "a better answer" are called outdated (BP, MA: about 15× tokens) | `CLAUDE.md:18-27`: one session by default, an agent only when evidence supports it | follow | — |
| 19 | Set `model` per agent (`haiku` for simple jobs); per-call model overrides frontmatter (SUB) | `CLAUDE.md:9-16` tiers; agents' frontmatter: scout haiku, reviewer sonnet, money-reviewer and verifier opus | follow | — |
| 20 | A read-only reviewer gets an enforced tool limit (BP) | `reviewer.md` / `money-reviewer.md` `disallowedTools: Edit, Write, NotebookEdit`; scout `tools: Read, Grep, Glob, Bash` | follow | — |
| 21 | Subagents do not see the conversation or output style: restate the rules in the delegation prompt (SUB) | `CLAUDE.md:25` "Give paths, ask for up to ~25 lines"; a reviewer gets the diff, not the reasoning | follow | — |

## Hooks, settings, permissions

| # | Anthropic recommends | We do | Verdict | Fix |
|---|---|---|---|---|
| 22 | Hooks that must not block: exit 0, keep them fast; an `async` hook or a short command (HK) | `task-contract.py` (~25 ms); new `self-improve-log.py` measured 24–27 ms including Python start, exits 0 on any error | follow | — |
| 23 | SessionEnd hooks get 1.5 s by default; raise it with a per-hook `timeout` (HK) | `settings.json` SessionEnd hook has `"timeout": 5` | follow | — |
| 24 | PreToolUse on `Skill` sees Skill tool calls; typed `/skill` goes through `UserPromptExpansion` (HK). The `Skill` `tool_input` schema is not in the docs | Hook on `PreToolUse`/`Skill`; its first live line (2026-11-12 17:59, `skill-creator`) proves `tool_input.skill` | follow | Typed `/name` commands are caught from transcripts (`<command-name>`) by `collect.py`, so no second hook on an undocumented input |
| 25 | `Stop` hook exit 2 to enforce "done means verified" (BP) | The contract hook reminds; nothing blocks | deliberately different | Tried and measured: replayed on 842 past turns, a "code edited, nothing run" Stop hook would have fired on 4 of 47 turns with edits, none on trading code (README "Tried and dropped"). Rework comes from weak proof, so the contract asks for proof in the final message instead |
| 26 | `bypassPermissions` "only in isolated environments … offers no protection against prompt injection" (PRM) | `settings.json:25` `defaultMode: bypassPermissions` on the owner's Mac | deliberately different | Owner decision (commit `6bf3676`): prompts cost more than they save. Deny rules still apply in bypass; see #5 for the one hard stop worth adding |
| 27 | Allow rules have no effect in bypassPermissions; `Grep(*)` / `Glob(*)` "adds nothing" (PRM, CLI warning) | `Read(*)`, `Grep(*)`, `Glob(*)` printed a warning on every `claude -p` | gap → fixed | Now `Read`, `Grep`, `Glob` |
| 28 | Sandbox reads `~/.ssh`, `~/.aws/credentials` by default; add credential deny rules (SBX) | No sandbox, no credential deny rules | deliberately different | The owner's work is SSH and AWS against their own boxes; a deny would block it. Re-check if an untrusted repo or MCP server is added |
| 29 | Transcripts are deleted after `cleanupPeriodDays` | Not set, so only the default retention | gap → fixed | `cleanupPeriodDays: 120`, so the weekly run has 30+ days of history to call a skill unused |

## Learning loop, context, headless, scheduled

| # | Anthropic recommends | We do | Verdict | Fix |
|---|---|---|---|---|
| 30 | Turn "anything you've had to correct twice" into a written instruction (BP); structured notes outside the context window (CE) | Lessons were saved only when the owner asked, or by the Skill Creator rule | gap → proposal (global CLAUDE.md, shown as a diff) + fixed (hooks, weekly skill) | `self-improve-log.py` hooks, `setup-self-improve` skill + weekly task, and the in-session rule below |
| 31 | `/clear` between unrelated tasks; stale context costs on every message (CST) | `task-contract.py` tells the model to hand off past 150k tokens | follow | — |
| 32 | Invoked skills survive compaction capped at 5,000 tokens each, 25,000 total; key instructions at the top of SKILL.md (CTX) | Hazards and preconditions sit at the top of the long skills (the backtest skill's "Hazards" start at line 23) | follow | — |
| 33 | `claude --bare -p` for scripted calls (HL) | `benchmark/run_arm.sh` runs plain `claude -p` | deliberately different | The benchmark measures the whole setup (hooks, skills, CLAUDE.md); `--bare` would remove the thing under test |
| 34 | Desktop scheduled tasks skip a run while the Mac sleeps and do one catch-up run on wake; write guardrails into the prompt (SCH) | `memory-staleness-audit` (Mon 09:30) and `setup-self-improve` (Mon 10:00) prompts carry their own rules | follow | — |
| 35 | An enabled plugin costs context on every turn; check `/plugin` context cost (PL) | One plugin, `claude-mem` | follow | Its cost goes in the weekly review if usage shows it unused |
| 36 | Output styles are instructions, not enforcement; custom ones need `keep-coding-instructions: true` (OS) | Default style; language and format rules in `CLAUDE.md:3-4` | follow | — |

## Proposed global `CLAUDE.md` change (shown to the owner, not applied)

One addition under `## Skill Creator` (`CLAUDE.md:39-40`) that extends that section rather than repeating it:

```diff
 ## Skill Creator
 After a repeatable, non-trivial procedure (judged by what you actually did), create or update a skill with `skill-creator` as part of finishing the task. First check project (`<repo>/.claude/skills/`) and personal (`~/.claude/skills/`) skills and update an overlapping one in place. Project scope for repo-specific knowledge, personal scope for cross-project habits. Skip one-offs and plain facts.
+When I corrected your approach during a task, write the lesson down in that same turn, before the final message: update the skill that led you wrong, or save a feedback memory (what I said, why, how to apply). A correction I had to make twice becomes a skill or rule line. Never weaken a safety rule this way (money paths, deletion, force-push, retired hosts): propose that instead. The weekly `setup-self-improve` run catches what a session missed.
```

Status: shown to the owner on 2026-11-12; applied only after their yes.
