## Orchestration: a plan per task
No fixed process and no mandatory stages. The goal is a result faster and better than one session working alone; pick whatever achieves that for this task.

- **You are the router.** Read the task, answer these three, say the answer in 1–2 lines, start at once. Build the team from the answers and attach nothing else. Revise when the task turns out different. No separate router agent: you already have the context, and an agent starts cold.
  1. **What would prove this is done?** Name the evidence: a real record, a log line, a live probe, a test that fails first. Get it before saying done.
  2. **What can run at once?** Independent parts, or independent evidence sources (logs, database, code, external system). One coupled thread is the normal case: stay in one context. Split by context, not by work type: plan, code and tests of one change stay together.
  3. **What is expensive to get wrong?** Add a fresh reviewer or verifier only there.
- **Add an agent only for** noisy output (logs, dumps, wide reads come back as a summary), breadth (a search or audit too wide for one pass), fewer tools (a reviewer that cannot edit), or fresh eyes (a reviewer that never saw the reasoning). A subagent on the same task gives no smarter answer, and it can be slower: it first has to gather the context you already have. Parallelism mostly buys thoroughness; it saves time only on truly independent parts. Writing code stays in one thread unless the parts are truly independent.
  | Task | Usually needs |
  |---|---|
  | Incident, "why did X happen" | gather logs, database and external state in parallel; name a cause only with a record id or log line |
  | Port a pattern from a sibling | read the source pattern first; copy it, add no new logic; parity check against the sibling |
  | Fix | reproduce first, with a failing test or probe; on critical code one independent reviewer, at most one re-check of the fix |
  | Data, report, page | solo, no verifier by default; parallel per data group if big; check numbers against the source |
  | Live test | solo; read the result back from the real system |
  | Deploy, ops | solo; re-read the real state afterwards |
  | Feature | one thread; agents per part only for independent parts, roughly over 3000 changed lines |
  | Audit, inventory | parallel readers per area |
  | Question, status | solo; short, plain words |
- **Done means proven.** Give the evidence: the command you ran and its output, or the record id and log line. Say in plain words what was proven, so the owner never has to ask "did you check it, did you push it". Short answers.
- **Never a serial chain.** Don't wait on an agent while an independent step is left; integrate results as they arrive. Don't use `fork` for delegated work: it inherits the main session's effort and whole context.
- **Bound the review.** A reviewer asked to find problems always finds something: give it explicit criteria and "report only gaps that affect correctness, skip style". One review, then one re-check that sees only the fix diff. What stays open goes in the report. A verifier must run the full check and try inputs that should fail, not one passing test.
- **Brief with paths, not file contents, and ask for a short return** (up to ~25 lines, no code or diffs). Give each agent a goal, what is already ruled out, and what to return. Check agent results before reporting them.
- **Report what was checked.** A finding from an agent is a claim until verified; what stays unchecked is marked "not verified".
- **When completeness matters**, pair a reader with a mechanical sweep and diff the two lists, for code and for data rows alike.
- **Roles**, when you do use agents. Set model and effort explicitly in the call:
  | Role | Agent type | Model / effort |
  |---|---|---|
  | collect, list, grep, dump | `scout` | haiku / low |
  | read, trace, inventory, docs research | default `general-purpose` (`Explore` only to locate code) | sonnet / medium; opus / medium on critical paths |
  | write ordinary code, mirror a pattern, tests | default `general-purpose` | sonnet / medium |
  | write critical code | default `general-purpose` | opus / medium |
  | review ordinary diff | `reviewer` | sonnet / medium |
  | review critical diff | `critical-reviewer` | opus / medium |
  | refute claims and findings | `verifier` | opus / medium |
- Writers in one repository each get `isolation: "worktree"`. Reviewers get the diff, not the author's summary.
