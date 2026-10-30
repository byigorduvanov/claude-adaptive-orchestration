# Results

One owner, real work, Claude Code with Opus 5.5, October 2026. Project details are left out. **Each number below is one run per task and arm.** It shows direction, not a precise measurement.

## What the owner's sessions look like

692 real Claude Code sessions, classified from truncated prompts by three Sonnet agents with `benchmark/classify_brief.md`. 40 were spot-checked by hand; the rest were not.

| Task type | Share | Sessions needing rework |
|---|---|---|
| Deploy, ops | 17% | 21% |
| Question, status | 15% | 16% |
| Agent tool setup | 13% | 22% |
| Incident, "why did X happen" | 12% | 42% |
| Live test | 9% | 24% |
| Data, report, page | 8% | 26% |
| Fix | 8% | 35% |
| Feature | 8% | 19% |
| Port a pattern from a sibling | 5% | 41% |
| Audit, inventory | 5% | 18% |

- Overall rework: 25%. The most common cause was a result nobody had proven.
- Only about 7% of sessions split into independent parts. That is a lower bound, judged from opening prompts, and it ignores parallel evidence gathering.

## A/B runs

Tokens are input-equivalents: cache read ×0.1, cache write ×1.25, output ×5. Time runs to the last write of the report.

**Broad audit of a live system.** Graded by a blind judge.

| Arm | Score | Time | Tokens |
|---|---|---|---|
| One session | 6.5 | 26.3 min | 3.35M |
| Fixed multi-agent rules, 6 parallel auditors | **8** | **18.5 min** | 6.06M |

**One fix on a money path.** One `critical-reviewer`-style grader per arm, same brief, running its own probes. The judge knew the mapping; the graders did not.

| Arm | Score | Time | Tokens | Worst defect found |
|---|---|---|---|---|
| One session | 6.25 | **12 min** | 1.78M | HIGH |
| Pipeline with one review, medium effort\* | 6.7 | 15 min | 1.55M | HIGH |
| Plan per task (this repo's approach) | 8.2 | 28 min | 2.08M | HIGH |
| Plan plus re-review of every later change | **8.5** | 36 min | 2.84M | MEDIUM |

**Triage of 806 findings from a validator.** One `verifier` grader per arm, same brief.

| Arm | Score | Time | Tokens |
|---|---|---|---|
| One session | **9.0** | **14.5 min** | 1.69M |
| Plan per task (this repo's approach) | 8.5 | 26 min | 1.90M |
| Pipeline with verifiers, medium effort\* | 8.0 | 16 min | 3.21M |

\* Graded with a slightly earlier version of the brief.

## What this shows

- **The goal of "faster and better than one session" was not met on small tasks.** The plan-per-task arm took about twice as long. It scored 2 points more on the money fix and no better on the triage.
- **An independent review moved the score on critical code.** On the data triage a verifier added time and no gain.
- **Parallel agents won on the broad task,** about 1.4× faster at about 1.8× tokens, and they found more. The earlier "4× faster" claim from this work was wrong; see below.
- **An unbounded review loop is expensive.** Four reviews in a row each found something new. The HIGH defect was gone, at three times the solo time.
- **No fix was ready to merge,** in any arm.

## Measuring mistakes worth avoiding

- **Cut wall time at the report.** `score.py` first read the end of the transcript and turned a 26-minute run into "81 minutes", because the session continued later. A second arm read 36 minutes instead of 23.7. Anthropic's `/doctor prompt-audit` caught the first one.
- **Give every arm the same grader brief.** Scores from different briefs are not comparable: the same solution went from 7.5 to 6.25 once graders ran their own probes.
- **Build the grader's fact list from data.** Here part of it came from two arms' reports, which favours those arms.
- **Check the version.** The arms did not all run the same CLI version.

## Not measured

Whether the plan-per-task rules reduce rework on real work. The next step is to classify new sessions and compare the rework share per type.
