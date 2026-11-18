# Results

One owner, real work, Claude Code with Opus 5.5, October–November 2026. Project details are left out. **Each number below is one run per task and arm.** It shows direction, not a precise measurement.

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

## Confirmed defects across the money-path tasks (rounds 6–8)

Every defect below was confirmed by the blind grader with a probe test or a code trace (grades: `.ab-r6/grade/T2*/GRADE.md`, `.ab-r7/VERDICT.md`, `.ab-r8/VERDICT.md` in the owner's workspace).

| Task | Pipeline | Vanilla |
|---|---|---|
| Fix of two bugs (round 6) | 1 MEDIUM + 2 LOW | 2 MEDIUM + 2 LOW |
| Large feature (round 7) | 1 MEDIUM + 1 LOW | 2 MEDIUM + 3 LOW |
| Smaller feature (round 8) | none | 1 LOW |
| **Total** | **2 MEDIUM + 3 LOW** | **4 MEDIUM + 6 LOW** |

The pipeline shipped fewer defects in each of the three tasks. With one run per arm, a 3-of-3 split would happen by chance about 1 time in 8 if the two were equal.

## Round 8 (2026-11-18): a second feature build, current rules + hooks + agents vs plain Claude Code

A replay of a second real feature, of a different kind: a Go data service that keeps the market caps live trading sizes
its take-profit levels from. The task was to fill the caps CoinGecko lacks from CoinMarketCap: one request per run, the
largest cap per ticker unless pinned, never overwrite a CoinGecko cap, and change nothing when CoinMarketCap is down.
Both arms got the base commit, the real build brief and spec as written that morning, and the owner's words. The answer
was hidden: no later commits, a leak-checked memory snapshot, and no access to the other repos or transcripts. The
terminal plan's 5-hour limit stopped the first launch before any work. Both arms were restarted fresh on the app account.

Grading was the same as round 7: one blind `money-reviewer` (opus/medium) per arm with one brief. The final feature's 14
real tests were ported as 11 requirement scenarios and 8 design/edge scenarios, plus probe tests for defects.

| Task | Arm | Score | Real scenarios (req / edge) | Time | Tokens | Agents | Worst defect |
|---|---|---|---|---|---|---|---|
| Feature build feeding a money path | Current rules | **9.5** | 11/11, 2/8 | 15.2 min | 1.54M | 1 `money-reviewer`, 2 rounds | none confirmed |
| | Plain | 9.0 | 11/11, **3/8** | 15.6 min | **1.14M** | 1 general-purpose reviewer | LOW: a listing whose cap fields all changed drops every filled cap at once |

- Both met every requirement in the same time. The 0.5-point gap is below the noise floor.
- The gap is one defect class. The rules arm's `money-reviewer` flagged "a readable answer with no caps wipes every
  filled cap" as HIGH, and the arm fixed it. The real feature's review found the same class. Plain's reviewer found no
  bug, and plain shipped that class. The plain arm's probe was run on the rules arm: it refuses that answer and keeps 4
  of 4 caps.
- Plain used 26% fewer tokens, and it marked caps from self-reported supply apart, as the real feature did.
- Neither arm built the real feature's price check against namesake coins. Each found the namesake risk on its own and
  closed part of it another way. Both arms changed the spec's "largest cap" rule; one scope rule was applied to both
  (−0.5 each).

**Rounds 7 + 8 together (two features, one run per arm each):** the rules never scored lower; the mean gap was +1.25
(+2.0 on a large money-path feature, +0.5 on a small one). Requirements were equal both times. The gap was always one
more confirmed defect in plain, of a failure-safety class the rules' reviewer caught. The time and token savings of
round 7 did not repeat. Reading: a small, consistent quality edge, not proof. That needs more features or repeat runs.

## Round 7 (2026-11-18): feature build, current rules + hooks + agents vs plain Claude Code

A replay of a real feature: a pre-buy token guard for a Rust copy-trader. The copier must never buy a token that has blacklist functions or has not been checked yet. Checks run off the hot path, and the guard prewarms tokens traded on the chain. Both arms got the base commit before the feature and the owner's real prompt, with the owner's three real answers given up front. The answer was hidden: no later commits, a memory snapshot without notes about the feature, and the reviewer's memory without the two bug classes found on it. There were no live orders. Same setup as round 6 otherwise. Both arms hit the terminal plan's 5-hour limit and were resumed at once in the same session on the app account (about 1 s pause).

Grading: one blind `money-reviewer` (opus/medium) per arm, with one brief. The final feature's 30 real tests were ported onto each arm's own API as 11 requirement scenarios and 8 design/edge scenarios, replaying the recorded chain data. Graders also wrote probe tests for defects and timed the hot path, base vs solution.

| Task | Arm | Score | Real scenarios (req / edge) | Time | Tokens | Agents | Worst defect |
|---|---|---|---|---|---|---|---|
| Feature build on a money path | Current rules | **7.3** | 10/11, **5/8** | **57.1 min** | **5.26M** | 2 `money-reviewer` | MEDIUM: one sell route (a hop kept in the router) can have its exit refused |
| | Plain | 5.3 | 10/11, 3/8 | 106.9 min | 7.21M | 1 general-purpose (medium), 3 review passes | MEDIUM ×2: exits to WETH can be refused; a proxy whose implementation delegates to an unknown target passes the blacklist check |

- The rules were ahead by 2 points, finished in about half the time and used 27% fewer tokens. That is above the ~1-point noise floor, but it is one run per arm with one grader per arm: a direction, not proof.
- Both met the same requirements (10/11, and both missed the same recheck order). The gap is defects: plain shipped one more MEDIUM and 3 LOW against 1 LOW, and its report called a blocked exit "missed buys, no money lost". The plain arm's bypass probe was run against the rules arm too, and the rules arm refuses that token.
- Plain built more: a buy-and-sell simulation per token, which the real feature had only proposed. It paid for that in time.
- Neither solution was ready to merge: both can refuse an exit on some sell routes. The real feature took 5 review rounds and about 7.5 hours, including live rounds.

## Round 6 (2026-11-17): current rules + hooks + agents vs plain Claude Code

Plain = no user `CLAUDE.md`, no hooks, no custom agents. Shared: skills, a memory snapshot from 10-31 (later notes could hold the answers), CLI 2.1.326, base commit, Opus 5.5 effort high; both arms of a task at once; graders blind, same brief as round 5, each wrote probe tests.

| Task | Arm | Score | Time | Tokens | Agents | Worst defect |
|---|---|---|---|---|---|---|
| One fix on a money path | Current rules | **9** | 22.5 min | 3.01M | 2 `critical-reviewer` | MEDIUM: a stale verify loop can close a new position on the same symbol |
| | Plain | 8 | **17.4 min** | **1.92M** | none | MEDIUM ×2: retries run out with no exit left; a failed stop on a flat venue published as STOP LOSS and re-entered |
| Triage of a validator's findings | Current rules | 9 | 18.2 min | **3.48M** | 1 general-purpose (medium) | 0 false claims |
| | Plain | **9.5** | **13.0 min** | 4.56M | 3 forks (inherit high effort) | 1 false claim (a row count) |

- Money fix: one point is at the noise floor (the same config scored 6.25 and 7.25 on this task). Price of the rules: +29% time, +57% tokens.
- Triage: a tie. Both covered all 638 (row, check) pairs with exact ids and missed the same bug (a signature error on non-ASCII symbols). Plain was 5 minutes faster; its forks inherited high effort and used 31% more tokens. The first attempt hit the terminal plan's 5-hour limit after 1.9 minutes; the rerun used the app account.
- Both solutions fixed both bugs with tests that fail on the base; neither was ready to merge.

## Round 5 (10-31): earlier, longer rules against one plain session

Both configs ran at once on the same CLI version, base commit, skills and memory, with the same grader brief. Labels stayed hidden until grading ended.

| Task | Arm | Score | Time | Tokens | Agents used | Worst defect |
|---|---|---|---|---|---|---|
| One fix on a money path | Current rules | **7.75** | 28.5 min | 2.00M | 1 `critical-reviewer`-style reviewer | MEDIUM |
| | One session | 7.25 | **18 min** | **1.20M** | none | HIGH |
| Triage of a validator's findings | Current rules | 8.8 | 14.8 min | 1.37M | none | n/a |
| | One session | 8.8 | 14.1 min | 1.23M | none | n/a |

- **Triage: a tie.** The current rules chose not to start any agents, and matched the plain session on time and score.
- **Money fix: the review is the difference.** It removed the only HIGH defect, at +10.5 minutes and +67% tokens. The 0.5-point gap itself is noise: the same plain-session config scored 6.25 and 7.25 on this task across two runs.
- **No solution was ready to merge.**
- **Not shown:** the current rules being faster than a plain session on small tasks, or their effect on a broad task or on rework. This is still one run per task.

## Earlier A/B runs

Earlier versions of the rules, kept for the history. Tokens are input-equivalents: cache read ×0.1, cache write ×1.25, output ×5. Time runs to the last write of the report.

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
| Plan per task, earlier version | 8.2 | 28 min | 2.08M | HIGH |
| Plan plus re-review of every later change | **8.5** | 36 min | 2.84M | MEDIUM |

**Triage of 806 findings from a validator.** One `verifier` grader per arm, same brief.

| Arm | Score | Time | Tokens |
|---|---|---|---|
| One session | **9.0** | **14.5 min** | 1.69M |
| Plan per task, earlier version | 8.5 | 26 min | 1.90M |
| Pipeline with verifiers, medium effort\* | 8.0 | 16 min | 3.21M |

\* Graded with a slightly earlier version of the brief.

## What the earlier runs showed

- **The goal of "faster and better than one session" was not met on small tasks.** The earlier plan-per-task version took about twice as long. It scored 2 points more on the money fix and no better on the triage; the latest test narrowed both gaps.
- **An independent review moved the score on critical code.** On the data triage a verifier added time and no gain.
- **Parallel agents won on the broad task,** about 1.4× faster at about 1.8× tokens, and they found more. The earlier "4× faster" claim from this work was wrong; see below.
- **An unbounded review loop is expensive.** Four reviews in a row each found something new. The HIGH defect was gone, at three times the solo time.
- **No fix was ready to merge,** in any arm.

## Measuring mistakes worth avoiding

- **Cut wall time at the report.** `score.py` first read the end of the transcript and turned a 26-minute run into "81 minutes", because the session continued later. A second arm read 36 minutes instead of 23.7. Anthropic's `/doctor prompt-audit` caught the first one.
- **Give every arm the same grader brief.** Scores from different briefs are not comparable: the same solution went from 7.5 to 6.25 once graders ran their own probes.
- **Build the grader's fact list from data.** Here part of it came from two arms' reports, which favours those arms.
- **Run both arms together.** In the earlier runs the arms did not all use the same CLI version or the same state of the data. Rerun both at once, with hidden labels.
- **Treat a gap under about a point as noise.** One config scored 6.25 and 7.25 on the same task.

## Reviewer evals and bug reconciliation (10-31)

- **Reviewer evals:** 2 of 3 passed, one run per case, graded by a small judge reading the report. Missed: a safety margin thinner than one price step.
- **Stop hook replay:** "code edited, nothing run after it" over 842 turns of 52 sessions in 14 days fired on 4 of 47 turns with edits, none on trading code. Dropped.
- **Automatic bug records vs. failure classes:** of 95 `bugfix` records in 14 days, 21 were about money code. 7 were covered by the reviewer's classes, 3 partly, 11 not, which gave 5 new classes. Sorted by hand from titles and the start of each record.
- **A record is not a fix.** One record said a bug was guarded, but the fix existed only in a benchmark arm and was never merged. Check the code, not the record.

## Rework recheck, blind (2026-11-17)

Sessions before the switch (2026-10-01..10-30) and after it (2026-10-31..11-17) mixed into one set, dates removed, shuffled, classified by three independent Sonnet agents with `benchmark/classify_brief.md`.

| | Before | After |
|---|---|---|
| Real sessions (majority not NOISE) | 122 | 55 |
| Needed rework, majority of 3 | 48 = 39% | 24 = 44% |
| Per classifier | 39 / 41 / 34% | 44 / 41 / 49% |
| Median prompts per session (no classifier) | 4 | 2 |
| Sessions with a correction word in a follow-up (regex) | 39% | 29% |
| Correction words per follow-up prompt (regex) | 0.16 | 0.19 |

Difference +4.3 points, 95% CI −11..+20: no measurable change. The three classifiers agreed on rework yes/no for 82% (before) and 75% (after) of sessions.

**Lesson:** the 2026-11-16 recheck reported "26% → 51%". It compared a three-agent classification of about 700 older sessions with a one-agent classification of 43 new ones. Classified together, blind, the gap shrinks to noise. Compare periods only inside one classification run.

## Causes of rework, and a replay of two fixes (2026-11-17)

The 24 "after" sessions flagged as rework by the majority above were split into 96 rework moments: an owner prompt that corrects, repeats or asks for proof. Each moment got one cause class from four Sonnet agents that read the transcript, or the claude-mem notes where the transcript was gone (12 of 24). Two sessions turned out to be false positives (a prompt sent twice; "continue" after an outage).

| Cause | Moments | Sessions | Already covered by a rule? |
|---|---|---|---|
| Wrong approach (misread goal, wrong data or scope) | 20 | 12 | partly: "say the scope you assume" (11-17) |
| Stopped early, ended on a "not done" list it could do itself | 15 | 11 | no |
| Report hard to follow: jargon, wall of detail, no "what do I do" | 13 | 7 | no |
| Asked what it could find or decide itself | 11 | 9 | yes: "questions go up front" (11-17) |
| Claimed without proof | 9 | 7 | yes: "verify it yourself" (11-12), "break it first" (11-17) |
| Unasked change | 7 | 6 | no |
| Slow, no ETA or cost estimate | 6 | 5 | partly: ETA rule (11-11, after all 5); no rule on limit cost |
| Harness, limit, outage | 6 | 6 | n/a |
| Replied in English after a pasted English brief | 4 | 4 | yes since 11-12 (3 of 4 cases were before it) |

Two fixes for the top uncovered causes were replayed on real moments with headless `claude -p` (Opus 5.5, effort high, no tools), current rules vs current rules + fix, 3 runs per case and arm, on the app account. Two blind Sonnet graders saw six shuffled outputs per case plus the owner's real next prompt; they agreed on 98 of 102 main grades.

| Fix | Cases | Before | After | Kept? |
|---|---|---|---|---|
| **A.** Report opens with what it means for me and what I must do; terms explained the first time; forwardable messages short | 8 | plain-words score 2.10 / 3; owner's follow-up made unnecessary 0.47 | 2.85 (better in 8 of 8 cases); 0.56; facts and proof kept 100% in both | **yes** |
| **B.** Before ending a turn, do what you still can; a "not done" list only holds what waits on the owner | 6 + 3 exempt | follow-up covered 0.17; owner-only action taken in exempt cases 4 / 18 | 0.18; 6 / 18 | **no**: no effect, slightly more overreach |

After a fresh review the kept wording was narrowed (only reports on work done or a problem found; "live" only as checked; proof stays in the reply; a plain question gets the answer first) and replayed again on the same 8 cases with a third blind grader: plain-words score 2.29 → 2.88, better in 6 of 8 cases, worse in none; facts kept 1.00 → 0.98.

What the replay cannot show: B's failure happens when the model decides on its own to stop. Asked directly "send or continue?", it chose "continue" in 16 of 18 target runs already without the fix, so the replay could not reproduce the failure. A's "as short as I asked" part did not work: a two-line message for a colleague stayed ~2.5k characters with and without it.

### Can a Stop hook catch "ended on a not-done list"? (2026-11-18)

Measured on final messages before any hook was written, threshold set in advance: catch most known cases, fire on at most 5% of turns in sessions with no rework.

| Detector | Known cases caught | Fires on clean turns (68) | Exempt cases (should pass, 3) |
|---|---|---|---|
| Keyword regex (uk/en/ru "not done / didn't wait / left") | 3 / 6 | 10 = 15% | — |
| Haiku judge on the final message | 4 / 6 | 48 = 71% | blocks 2 |

Neither passes, so no hook. Half the known cases are omissions (a venue left out, commit state not said), not a "not done" list, so no text pattern sees them. The step-6 text rule was then removed (2026-11-18): no measured effect in the replay, the first version took more owner-only actions, and the Claude app already tells the model every turn that a piece left undone is still its task. The next blind rework recheck tracks the share of "stopped early" moments.

## Not measured

More than one run per arm, and a broad multi-part task on the current rules.
