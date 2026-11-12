# Global rules

My real `~/.claude/CLAUDE.md`. Left out: the section with private operational details (hosts, accounts, deploy rules).

## Language
Reply in the language of my latest message. Code, identifiers, commands, logs, error messages, API and library names, plans and code comments stay in English unless the project clearly uses another language. When I write in Ukrainian: discuss and summarise in Ukrainian, keep technical artifacts and exact terms in English. AskUserQuestion text, labels and descriptions follow the conversation language too.

## Personal assistant
Everyday tasks (tickets, documents, personal research) belong to the assistant folder `~/assistant`, not to code projects. Facts about me live in its `vault/` (start from `vault/index.md`): read it before asking me something personal, and write new personal facts there, never into a code project's memory.

## Subagent model: choose it, never inherit by default
Every Agent / Workflow `agent()` call sets `model` and `effort` explicitly; omitting them inherits this session's most expensive settings.
- `haiku` / `medium` — mechanical, no judgement: grep/list/collect, file listings, formatting, one-line lookups.
- `sonnet` / `medium` (`high` only for the `reviewer` agent) — reading and summarising: docs / API research, codebase exploration, mapping where something lives, mirroring an existing pattern 1:1, reviews of non-money code, test scaffolding.
- `opus` / `medium`, always, money-path writers included — code that places, sizes, cancels or closes real orders, touches live accounts or money paths, cross-repo design, concurrency/race fixes, adversarial verification of a money-critical claim, anything where a subtle mistake is expensive.
No tier goes above `high`. `low` explores less, so on a real change it can miss a second fill/close path. Unsure between two tiers: the cheaper for read-only work, the stronger for anything that writes trading code. Say in one line which model each agent got and why.
Custom agent types (`~/.claude/agents/*.md`) replace the default system prompt and lose recall on inventory tasks: readers, researchers and code tracers run as the default `general-purpose` type, `Explore` only locates code, custom types only for narrow roles (verifier, reviewer, mechanical work).
At most 20 agents per workflow or per turn. Verify claims in batches per agent, not one agent per claim.

## Orchestration
Work in one session by default. Add an agent only when evidence supports it.
- Before starting, say in 1–2 lines: what proves this is done, what can run at once, what is expensive to get wrong.
- Done means proven: the command and its output, or a trade id and log line.
- On a diff that can move money, run one fresh `critical-reviewer` in the background with explicit criteria, "skip style". Ask it to name the class of bug, so every instance gets fixed. Re-check only the new diff. Stop after 3 rounds and rethink; on ordinary money fixes one re-check is enough. If you skip it, say so.
- Agents are for truly independent parts (a broad audit, a large migration), or for noisy output returned as a short summary. Writers stay in one thread. Give paths, ask for up to ~25 lines. A fork inherits this conversation: use it for a side task that needs this context, never for a reviewer, who must not see the reasoning.
- When a real money incident or a confirmed money bug is understood, add its failure class and an eval case without being asked: skill `reviewer-evals`.
- Tests and sweeps print a few lines and log details to a file.
- A finding from an agent is a claim until checked; mark what is not verified.
- Re-test these rules on each new model. Ask what you can stop doing.

## Git Sync Before Working
Before editing code in any git repo (in a multi-repo workspace: each repo separately):
1. `git fetch <remote>` for the repos the task touches only.
2. Clean tree and a real fast-forward → `git merge --ff-only` without asking.
3. Dirty tree, only behind → ff if `git diff --name-only HEAD..<remote>/<branch>` has no overlap with my uncommitted files. Overlap or diverged → stop and tell me.
4. Fetch failed → proceed, note that freshness is not verified.

## Context7 MCP
Use Context7 MCP unasked when a task depends on the docs, setup or configuration of a specific library/framework version or API surface.

## Skill Creator
After a repeatable, non-trivial procedure (judged by what you actually did), create or update a skill with `skill-creator` as part of finishing the task. First check project (`<repo>/.claude/skills/`) and personal (`~/.claude/skills/`) skills and update an overlapping one in place. Project scope for repo-specific knowledge, personal scope for cross-project habits. Skip one-offs and plain facts.

## Typo Check
At the end of every response, list typos found in my latest message under `**Typos:**`. No typos — omit the section.

## Speed: parallel and background by default
- Independent tool calls go in ONE message.
- Independent per-repo/per-exchange loops run in parallel (`( … ) &` + `wait`, or `xargs -P`), each item to its own log with a per-item `EXIT=` line. Ordered steps stay sequential (deploy order, merge-then-bump, anything sharing one remote dir or one PM2 app).
- Don't ask about reversible or minor choices: pick a default, keep going, state it in the summary. Ask only about prod, real money (live trading behaviour, order size, accounts), deleting things, anything irreversible, or expected behaviour you cannot find in code, logs or memory. Collect unavoidable questions into one AskUserQuestion (up to 4) and keep doing the work that doesn't depend on the answers.
- Long waits (`gh run watch`, long builds, soaks, backtests) go to `run_in_background`; never sit in a foreground watch/sleep.
- Every long job gets an ETA when you start it: minutes and wall-clock time, plus the basis (a measured rate, a prior run, or a guess marked as a guess). Make the job print `[n/N]` and re-estimate from the real rate.

## Verify before reporting
- Run the repo's own build, vet and test commands before reporting.
- After any remote or destructive action, re-read the real state with an independent check (re-list, `git ls-remote`, `gh api`, `pm2 jlist`, the endpoint itself) and quote that evidence.
- A 404, an empty list, empty output or a zero exit code is NOT proof on its own: first confirm the check works on a known-existing case. If it can't be trusted, say "not verified", never "done".

## Clean up processes you started
When a task is finished, stop what this session started and no longer needs: dev servers, backtests, soaks, watchers, port-forwards, ssh tunnels, background shells. Leave only what is meant to keep running and say what and why. Never kill processes another session or I started.

Killing a parent does not kill its children. After any abnormal end of a local run, and before closing a turn that ran a process pool or heavy local job, check for orphans: `ps -axo pid=,ppid=,etime=,command= | awk '$2==1 && /spawn_main|resource_tracker|loky/'`. Kill the ones from your runs and report the count; older ones are someone else's — report, don't kill. A process pool you write gets a parent-death guard in the worker initializer (a thread that `os._exit`s once `os.getppid()` changes).
