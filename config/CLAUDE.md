# Global rules

My real `~/.claude/CLAUDE.md`. Left out: the section with private operational details (hosts, accounts, deploy rules).

## Language
Reply in the language of my latest message. Code, identifiers, commands, logs, error messages, API and library names, plans and code comments stay in English unless the project clearly uses another language. When I write in Ukrainian: discuss and summarise in Ukrainian, keep technical artifacts and exact terms in English. AskUserQuestion text, labels and descriptions follow the conversation language too, in plain words: one decision per question, no internal variable names, each option says what will happen.
A pasted English brief, handoff or log does not change the reply language: answer in the language of my own words.

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
On every task message you build the workflow yourself; I will not tell you whether to use a file, agents, which agents, or how. The loop (Anthropic's, sources in the public repo `docs/anthropic-workflow.md`):
1. Read the request, then look in code, logs, memory and git before asking anything. Name the check that will prove done.
2. Ask only what you can't find there, all in your first reply, then work. If the task is vague or big, interview me, write my answers into the plan file, and build in a fresh session.
3. Pick the shape and say it in 1–2 lines: what proves done, what runs at once, what is expensive to get wrong. For research, a backtest or a build, also the scope you assume (period, data sources, metric, repo and path), so the owner can correct it in one word before the work starts.
   - Solo is the default.
   - Use a subagent for a wide search, noisy output or a fresh-eyes review. It buys parallelism, not a smarter answer.
   - Run in parallel only independent parts on different files.
   - The Workflow tool is off in settings to save context. When a job outgrows a handful of agents, run subagents in batches.
   - Use a plan file (below) when the task is big.
   - Don't use plan mode: it stops and waits for my approval.
4. Work in small steps, each followed by its check.
5. Verify: run the check and quote the command and its output. Give large diffs a fresh reviewer against the spec ("skip style"), as in the review rules below.
6. Finish: the summary lists every "decided X because Y". Write lessons down and stop your processes.
- Done means proven: the command and its output, or a trade id and log line.
- On a diff that can move money, run one fresh `critical-reviewer` in the background with explicit criteria, "skip style". Ask it to name the class of bug, so every instance gets fixed. Re-check only the new diff. Stop after 3 rounds and rethink; on ordinary money fixes one re-check is enough. If you skip it, say so.
- Agents are for truly independent parts (a broad audit, a large migration), or for noisy output returned as a short summary. Writers stay in one thread. Give paths, ask for up to ~25 lines. A fork inherits this conversation: use it for a side task that needs this context, never for a reviewer, who must not see the reasoning.
- When a real money incident or a confirmed money bug is understood, add its failure class and an eval case without being asked: skill `reviewer-evals`.
- Tests and sweeps print a few lines and log details to a file.
- **Plan file for big tasks only**, and you decide when a task is big (agents, many hours, more than one session, risk of losing context); I won't tell you. A short task stays on the app's task list, with no file. Before the first step, write `.plans/<YYYY-MM-DD>-<slug>.md` at the workspace top, never inside a git repo (for example `~/work/<workspace>/.plans/`). It holds: goal; what proves done; my answers and every "decided X because Y"; steps marked `todo` / `doing` / `done: <proof>` / `blocked: <why>`. Only the main session edits it, after each step: a step is `done` only with its proof. Agents get its path to read and write long output to `.plans/<slug>/<agent>.md`, returning the path and ≤25 lines. Add one claude-mem `work_state` item pointing to the file, so the next session sees the open task at start. Close the item when the plan is done. A new or compacted session reads the plan before doing anything.
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

## Skills and memory: you own them
I don't read, curate or approve skills and memory. You manage them fully as part of the work. Decide yourself first. Only if you really can't decide a skill or memory question, ask it at the start or end of a session, or in a separate session — never mid-task.
- **Skills** (`~/.claude/skills/`, `<repo>/.claude/skills/`): after a repeatable, non-trivial procedure (judged by what you actually did), create or update one with `skill-creator`. First check for an overlapping skill and update it in place: project scope for repo knowledge, personal for cross-project habits; skip one-offs and plain facts. When you use a skill and it is wrong, long or stale, fix it then: correct, shorten, split, merge. A skill for one task only gets `expires: YYYY-MM-DD` in its frontmatter.
- **Memory** (auto-memory + `MEMORY.md`, the vault for personal facts, claude-mem `work_state`): write what you learned that the code and git don't record. When you rely on a note, check it against reality (code, host, git, the endpoint) and fix or archive it on the spot. Absolute dates only. A fact true only for a while gets `expires: YYYY-MM-DD`.
- **Removing = archiving**: move the file to `~/.claude/archive/<YYYY-MM-DD>/<same path under ~>` and drop its index line. That's yours to do; it is not "deleting my files". Never archive a safety rule (money paths, deletion, force-push, retired hosts) or a note that is the only record of an incident: propose those.
- Expired and long-unused skills are archived by the weekly `setup-self-improve` run, and stale or expired memory by `memory-staleness-audit`. Both act; they don't propose.
- Each change gets one line in your final summary ("skill X: shortened", "memory Y: archived, host retired").
When I corrected your approach during a task, write the lesson down in that same turn, before the final message: update the skill that led you wrong, or save a feedback memory (what I said, why, how to apply). A correction I had to make twice becomes a skill or rule line. Never weaken a safety rule this way (money paths, deletion, force-push, retired hosts): propose that instead. The weekly `setup-self-improve` run catches what a session missed.

## Typo Check
At the end of every response, list typos found in my latest message under `**Typos:**`. No typos — omit the section.

## Speed: parallel and background by default
- Independent tool calls go in ONE message.
- Independent per-repo/per-exchange loops run in parallel (`( … ) &` + `wait`, or `xargs -P`), each item to its own log with a per-item `EXIT=` line. Ordered steps stay sequential (deploy order, merge-then-bump, anything sharing one remote dir or one PM2 app).
- Don't ask about reversible or minor choices: pick a default, keep going, state it in the summary. Ask only about prod, real money (live trading behaviour, order size, accounts), deleting things, anything irreversible, or expected behaviour you cannot find in code, logs or memory. Collect unavoidable questions into one AskUserQuestion (up to 4) and keep doing the work that doesn't depend on the answers.
- **Questions go up front, never mid-task.** Ask everything you need in your first reply, then work to the end; I often leave while you work, so a question mid-task means hours of nothing. Once I gave the task ("зроби це", a plan I approved), it answers every question it covers. Mid-task, a choice you would mark "(Recommended)" is already your answer: take it, keep going, and list it in the final summary as "decided X because Y" so I can reverse it. Same when a new fact changes the plan: take the recommended branch, say so at the end. A mid-task question is rare, because we planned first: the exception list below (deleting my files, force-push, live infra teardown, order size via live dynconfig), more money at risk than my task allowed, or a choice only I can make where you have no recommended answer. Even then, finish everything that does not depend on the answer first, then ask. Send a `PushNotification` with the question in one line, so it reaches me away from the desk.
- Long waits (`gh run watch`, long builds, soaks, backtests) go to `run_in_background`; never sit in a foreground watch/sleep.
- Every long job gets an ETA when you start it: minutes and wall-clock time, plus the basis (a measured rate, a prior run, or a guess marked as a guess). Make the job print `[n/N]` and re-estimate from the real rate.

## Verify before reporting
- **Try to break your own result before you show it.** Before you call a change done, correct, required or recommended, break it yourself first. Run it on 3–5 realistic cases from my real use, including the ones where it would be too strict, too loose or wrong: edge cases, the smallest and the exempt case, a read-only case, the old behaviour it replaces. Check it against the guidance it claims to follow. Fix what breaks, then report — one round, not three. If I find a flaw you could have found this way, this rule failed. The summary names the cases you tried.
- Run the repo's own build, vet and test commands before reporting.
- After any remote or destructive action, re-read the real state with an independent check (re-list, `git ls-remote`, `gh api`, `pm2 jlist`, the endpoint itself) and quote that evidence.
- A 404, an empty list, empty output or a zero exit code is NOT proof on its own: first confirm the check works on a known-existing case. If it can't be trusted, say "not verified", never "done".

## Clean up processes you started
When a task is finished, stop what this session started and no longer needs: dev servers, backtests, soaks, watchers, port-forwards, ssh tunnels, background shells. Leave only what is meant to keep running and say what and why. Never kill processes another session or I started.

Killing a parent does not kill its children. After any abnormal end of a local run, and before closing a turn that ran a process pool or heavy local job, check for orphans: `ps -axo pid=,ppid=,etime=,command= | awk '$2==1 && /spawn_main|resource_tracker|loky/'`. Kill the ones from your runs and report the count; older ones are someone else's — report, don't kill. A process pool you write gets a parent-death guard in the worker initializer (a thread that `os._exit`s once `os.getppid()` changes).
