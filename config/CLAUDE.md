# Global rules

My real `~/.claude/CLAUDE.md`. Left out: the section with private operational details (hosts, accounts, deploy rules).

## Language
Reply to the user in the language of the user's latest message by default.

For technical work, use English for code, identifiers, commands, logs, error messages, API names, library names, documentation terms, implementation plans, and code comments unless the project clearly uses another language.

When the user writes in Ukrainian, understand and discuss the task in Ukrainian, but keep technical artifacts and exact technical terminology in English for precision. Final summaries and explanations to the user should be in Ukrainian unless explicitly asked otherwise.

This applies to interactive prompts too, not just prose: when using AskUserQuestion (or any similar tool that shows the user a question/options to pick from) while the conversation is in Ukrainian, write the question text and option labels/descriptions in Ukrainian as well — never default to English there just because the tool schema itself is in English.

## Subagent model: choose it, never inherit by default
Every Agent / Workflow `agent()` call sets `model` deliberately — omitting it inherits this session's (most expensive) model, which is a choice too and must be justified, not an accident.
- `haiku` — mechanical, no judgement: grep/list/collect, file listings, formatting, one-line lookups.
- `sonnet` — reading and summarising: official docs / API research, codebase exploration (Explore), mapping where something lives, mirroring an existing pattern 1:1 (a knob copied from a sibling), reviews of non-money code, test scaffolding.
- `opus` — code that places, sizes, cancels or closes real orders, touches live accounts or money paths, cross-repo design, concurrency/race fixes, adversarial verification of a money-critical claim, and anything where a subtle mistake is expensive.
When you spawn agents, say in one line which model each got and why. If unsure between two tiers, take the cheaper one for read-only work and the stronger one for anything that writes trading code.
Effort follows the tier: pass `effort` explicitly on every Agent / `agent()` call — `haiku` → `medium`, `sonnet` → `medium` for reading and research (`high` only for the `reviewer` agent), `opus` → `medium`, money-path writers included. On Opus 5.5, medium matched high on money-code tasks and ran 17% faster, and medium matched max on reading and verification. Low passes small, fully specified tasks but explores less (31–54% of an inventory), so on a real change it can miss a second fill/close path. Opus agents are always `medium`, no exceptions; no tier goes above `high`. The main session stays Opus `high` (`modelSettings`), so an omitted `effort` would give an Opus agent `high`: always pass it.
Custom agent types (`~/.claude/agents/*.md`) replace Claude Code's default system prompt: on a code-inventory task (09-22) a custom `reader` fell to 0.26–0.55 recall vs 0.87–0.90 for the default type. Readers, researchers and code tracers run as the default `general-purpose` type with `model` + `effort` set in the call, and `Explore` only locates code; custom types only for narrow, tightly bounded roles (verifier, reviewer, mechanical work), with short bodies.
Size cap: at most 20 agents per workflow or per turn of Agent calls (settings `workflowSizeGuideline: unrestricted` + env `CLAUDE_CODE_WORKFLOW_SIZE_WARNING_AGENTS=20`, so this line is the only size guideline). Verify claims in batches per agent, not one agent per claim.

## Orchestration
Work in one session by default. Add an agent only when evidence supports it.
- Before starting, say in 1–2 lines: what proves this is done, what can run at once, what is expensive to get wrong.
- Done means proven: the command and its output, or a trade id and log line.
- On a diff that can move money, run one fresh `critical-reviewer` in the background with explicit criteria, "skip style". Ask it to name the class of bug, so every instance gets fixed. Re-check only the new diff. Stop after 3 rounds and rethink the approach; on ordinary money fixes one re-check is enough. If you skip it, say so.
- Agents are for truly independent parts (a broad audit, a large migration), or for noisy output returned as a short summary. Writers stay in one thread. Give paths, ask for up to ~25 lines. Set model and effort in the call. A fork inherits this conversation and shares its cache: use it for a side task that needs this context, never for a reviewer, who must not see the reasoning.
- When a real money incident or a confirmed money bug is understood, add its failure class and an eval case without being asked: skill `reviewer-evals`.
- Tests and sweeps print a few lines and log details to a file.
- A finding from an agent is a claim until checked; mark what is not verified.
- Re-test these rules on each new model. Ask what you can stop doing.

## Git Sync Before Working

Before editing code in any git repository — including each individual repo inside a multi-repo workspace — make sure the local branch actually reflects what's on the remote, since a teammate may have pushed since your last pull and there's no hook doing this automatically:

1. `git fetch <remote>` for the specific repo(s) the task touches (don't blanket-fetch an entire large workspace unless asked).
2. If the working tree is clean and the local branch is a strict ancestor of `<remote>/<branch>` (a real fast-forward), run `git merge --ff-only` (or `git pull --ff-only`) automatically — do not ask first, this never rewrites or loses local history.
3. If the tree is dirty and the branch is only behind, compare the incoming remote diff (`git diff --name-only HEAD..<remote>/<branch>`) against your uncommitted files; if there's no file overlap, the ff/pull is still safe to do automatically. If there is overlap, or the branch has diverged (ahead and behind at once), stop and tell the user what's out of sync instead of merging blindly.
4. If a fetch fails (offline, auth), don't block the task on it — proceed with a note that freshness couldn't be verified.

## Context7 MCP
Use Context7 MCP, without me having to ask, when a task depends on the documentation, setup or configuration of a specific library/framework version or API surface, instead of recalling it from memory.

## Skill Creator
Whenever you carry out a repeatable, non-trivial procedure (judged by what you actually did, whether I dictated the steps or not), use `skill-creator` to create or update a skill as part of finishing the task — don't wait to be asked. Typical substance: server access and hardening, deploys and releases, commit/PR and review conventions, a recurring bug class, containers, secrets/env layout, monitoring and alerting, audits, API integration patterns, DNS/SSL/proxies, backup and rollback, dev-env bootstrap, testing conventions, cloud provisioning, research methods, repo structure. First check project (`<repo>/.claude/skills/`) and personal (`~/.claude/skills/`) skills and update an overlapping one in place; create a new one only when nothing close exists. Project scope for repo-specific knowledge, personal scope for cross-project habits. Skip one-offs and plain facts (those belong in CLAUDE.md or memory).

## Typo Check
At the end of every response, list any typos or spelling mistakes found in the user's latest message under a `**Typos:**` section. If there are no typos, omit the section entirely.

## Speed: parallel and background by default
- Independent tool calls go in ONE message (several Read/Bash/WebFetch at once), not one per turn.
- Per-repo/per-exchange loops whose iterations don't depend on each other (builds, tests, `go vet`, `git fetch`, ssh probes, scp to different hosts) run in parallel: `( … ) &` per item + `wait`, or `xargs -P`. Write each item's output to its own log/file and print a per-item `EXIT=` line, so a failure in one is not hidden by the others. Keep ordered steps sequential (deploy order, merge-then-bump, anything sharing one remote dir or one PM2 app).
- Don't stop to ask about reversible or minor choices (naming, file layout, which of two equivalent approaches, test shape, default values that are easy to change later): pick a sensible default, keep going, and state what you picked in the final summary. Ask only about prod, real money (live trading behaviour, order size, accounts), deleting things, anything irreversible, or expected behaviour you cannot find in code, logs or memory. When questions are unavoidable, collect them and ask once in a single AskUserQuestion (up to 4 questions), not one at a time over the session; keep doing the work that doesn't depend on the answers.
- Long waits do not block the session: `gh run watch`, `gh pr checks --watch`, long builds, soaks and backtests go to `run_in_background`, and the session meanwhile does the next step that doesn't need their result. Never sit in a foreground watch/sleep.
- Every background or long job (downloads, fetches, backtests, sweeps, builds, deploys, CI) gets an expected time when you start it, before I have to ask: give the ETA in minutes and a wall-clock time, then the basis for it — a measured rate (items/min from the log, a prior run of the same job) or, before any rate exists, a rough guess you mark as a guess. Once the first progress lines exist, re-estimate from the real rate and say if it moved. Make the job print progress (`[n/N]`) so the rate can be measured.

## Verify before reporting
- Run the repo's own build, vet and test commands before reporting.
- After any remote or destructive action (deleting branches/files/resources, pushes, merges, deploys, API writes, config changes on a box), re-read the real state with an independent check (re-list, `git ls-remote`, `gh api`, `pm2 jlist`, the endpoint itself) and quote that evidence in the summary.
- A 404, an empty list, an empty output or a zero exit code from a check is NOT proof of success on its own — first confirm the check itself works (it returns the thing on a known-existing case, the URL/owner/repo/auth are right). If the check can't be trusted, say "not verified", never "done".

## Clean up processes you started
When a task is finished, stop the processes this session started that are no longer needed: dev servers (`vite`, `npm run dev`), backtests, soaks, `tail -f`/watchers, port-forwards and ssh tunnels, background shells. Leave running only what is meant to keep running (PM2 apps, deployed services, something I asked to keep up), and say in the summary what was left running and why. Never kill processes another session or I started.

Killing a parent does not kill its children. Whenever a local run of yours ends abnormally (Bash timeout, TaskStop, interrupt, killed background shell) and before closing any turn that ran a process pool or a heavy local job (backtests, `ProcessPoolExecutor`/`multiprocessing`, joblib, node workers), check for orphans it left: `ps -axo pid=,ppid=,etime=,command= | awk '$2==1 && /spawn_main|resource_tracker|loky/'`. Kill the ones from your runs and report the count; ones that predate your run belong to someone else, so report them and do not kill them. 10-28: 45 idle orphaned backtest workers from killed runs pushed swap to 9.5 GB and the SSD to ~200 GB/day on my 8 GB Mac. When you write a process pool, give the worker initializer a parent-death guard (a thread that `os._exit`s once `os.getppid()` changes): spawn workers never see EOF when the parent dies.
