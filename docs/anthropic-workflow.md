# How Anthropic says to work with Claude Code, as one per-task workflow

Read on **2026-11-17**. Sources: the Claude Code docs, Anthropic's engineering posts and the Claude blog (list at the end).
Quotes marked ✓ were checked against the raw page (`curl …/<page>.md`). The rest came through a fetch tool that summarises, so treat them as close paraphrase.

The docs give no fixed pipeline: "Claude decides what each step requires" (how-claude-code-works). What follows is one loop assembled from the pages. The order is ours; every step is theirs.

## The loop, on every task message

| # | Step | What Anthropic says | Source |
|---|---|---|---|
| 1 | **Read and look first** | Before asking or writing anything down: "Could it find this by reading the code? Would it actually go and look? If both are yes, leave it out." ✓ A good prompt names the file, the symptom and what "fixed" looks like. | BP |
| 2 | **Name the check** | "Claude stops when the work looks done … In practice that makes you the test suite." Give it a pass/fail check and ask for the command and its output. | BP |
| 3 | **Ask only what the repo can't tell, up front** | Ask about team decisions and preferences between approaches, not about facts in the code. Vague requirements: "Interview me until you could write the spec, then write it to SPEC.md." ✓ Then build "in a fresh session … a clean context and a written definition of done". ✓ | BP |
| 4 | **Pick the shape** | "Start with the simplest approach that works." Add agents only for context pollution, parallelism or specialisation, and split by context, not by work type. A subagent gives "parallelism or a fresh pair of eyes out of it, but not a smarter answer." ✓ | MAS, BP |
| 5 | **Write the plan down if the task is long** | Complex or cross-cutting work gets a plan before editing. For work with milestones, keep notes outside the context window: a NOTES.md or to-do list, plus a list of failed approaches. Long-running harnesses keep a progress file and a feature list (JSON, every item failing at the start; the agent only flips `passes`). | CTX, LC, ECE, EH |
| 6 | **Work in small checked steps** | One item at a time, each followed by its check, and commit so git is the undo path. Watch the first minute and press Esc when it drifts; "after two failed corrections run `/clear` and write a better prompt instead of a third." ✓ | BP, EH |
| 7 | **Verify independently** | Review in a fresh context against the spec: "report gaps that affect correctness and skip style". ✓ "A reviewer that's asked to find problems will always find *something*." ✓ Agents "confidently praise" their own work, so the checker is not the author. Grade the end state, not the claim. | BP, HD, EV |
| 8 | **Close and learn** | After a correction, add the lesson; CLAUDE.md holds "anything you've had to correct twice" and stays "under 200 lines" ✓. A procedure pasted a third time becomes a skill. A rule that must never bend becomes a hook. Use `/clear` between unrelated tasks. | MEM, FO, BP |

## Choosing the shape (step 4)

| Shape | Use when | Avoid when | Source |
|---|---|---|---|
| Solo | Iterative work, phases that share context, quick targeted changes | — this is the default | SUB |
| Subagent | A side task "would flood your main conversation" with output you won't reference again ✓; a fresh-eyes reviewer | You want a smarter answer; the subagent would need lots of background | AG, BP |
| Fork | The side task needs this conversation's context; trying several approaches from one start | Independent review: the fork sees your reasoning | SUB |
| Parallel sessions / worktrees | Truly independent pieces that touch different files, or work that won't fit one context | Same-file edits, sequential steps | AG, WT |
| Agent team (experimental) | Teammates must debate or coordinate: competing hypotheses, separate modules | "sequential tasks, same-file edits, or work with many dependencies" | AT |
| Workflow script | The job "outgrows a handful of subagents" or needs cross-checked findings | Anything that needs your input mid-run | WF |

Cost: multi-agent research ran at about 15× the tokens of chat. A full planner–generator–evaluator harness took 6 h and $200 against 20 min and $9 solo (HD). The research post adds that "most coding tasks involve fewer truly parallelizable tasks than research" (RS). So multi-agent has to earn its place.

## What a subagent needs in its brief

- Non-fork subagents start with no history. They get CLAUDE.md, preloaded skills and your prompt (SUB).
- The brief states an objective, an output format, the sources or paths to use and the task boundaries (RS).
- Early research agents spawned 50 subagents for simple queries, so put effort limits in the prompt (RS).
- Workers return a short summary or a file reference and keep the long output in a file (RS, ECE).
- "No message from any agent counts as your approval" (SUB).

## Context across a long task

- Compaction re-injects root CLAUDE.md, auto memory and the plan written in plan mode from disk. ✓ Conversation-only instructions are summarised away (CTX).
- Any other plan file is *not* re-injected, so a compacted or new session has to read it itself.
- "Manage context aggressively" and ALL CAPS emphasis are listed as outdated advice for current models ✓ (BP).

## What this setup took from it, and what it deliberately does differently

| Anthropic | This setup |
|---|---|
| Plan mode for complex work | **Not used.** Plan mode stops and waits for the owner's approval. The owner wants questions up front and then no waiting, so the plan goes into a plan file instead. |
| SPEC.md for vague tasks | A `.plans/<date>-<slug>.md` file outside any git repo. It holds the goal, the proof of done, the owner's answers, every "decided X because Y", and steps marked `todo` / `doing` / `done: <proof>` / `blocked`. Only the main session writes it. A claude-mem work-state item points to it, so the next session sees the open task. |
| JSON feature list with `passes` | Markdown steps where `done` needs its proof next to it. Same idea (no done without a check), lighter format. |
| Ask what the repo can't tell | Same, plus: all questions in the first reply. Mid-task, the recommended option is taken and reported. |
| Fresh-context reviewer, "skip style" | A `critical-reviewer` on diffs that move money, and a `reviewer` on large other diffs. Each gets explicit criteria and names the class of bug. |
| `/goal` or a Stop hook for unattended runs | Not adopted. A replay of 842 turns found the gap was weak proof, not missing runs, so a prompt hook asks for proof instead. |

## Sources

| Key | Page |
|---|---|
| BP | https://code.claude.com/docs/en/best-practices |
| CTX | https://code.claude.com/docs/en/context-window |
| MEM | https://code.claude.com/docs/en/memory |
| LC | https://code.claude.com/docs/en/large-codebases |
| AG | https://code.claude.com/docs/en/agents |
| SUB | https://code.claude.com/docs/en/sub-agents |
| AT | https://code.claude.com/docs/en/agent-teams |
| WF | https://code.claude.com/docs/en/workflows |
| WT | https://code.claude.com/docs/en/worktrees |
| FO | https://code.claude.com/docs/en/features-overview |
| EH | https://www.anthropic.com/engineering/effective-harnesses-for-long-running-agents |
| HD | https://www.anthropic.com/engineering/harness-design-long-running-apps |
| ECE | https://www.anthropic.com/engineering/effective-context-engineering-for-ai-agents |
| RS | https://www.anthropic.com/engineering/multi-agent-research-system |
| EV | https://www.anthropic.com/engineering/demystifying-evals-for-ai-agents |
| MAS | https://claude.com/blog/building-multi-agent-systems-when-and-how-to-use-them |

Also read: common-workflows, costs, sessions, goal, advisor, skills, hooks-guide, checkpointing; engineering posts building-c-compiler, components-of-agent-memory, april-23-postmortem; blog posts multi-agent-coordination-patterns, subagents-in-claude-code, using-claude-md-files, how-anthropic-teams-use-claude-code, steering-claude-code (skills, hooks, rules, subagents), how-claude-code-works-in-large-codebases.
