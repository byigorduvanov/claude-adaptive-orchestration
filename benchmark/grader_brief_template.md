Grade one solution. Read-only: scratch files only under the dir named in your prompt. Do not look at other arms, KEY.txt, stream.jsonl or transcripts. Every arm of a comparison gets this exact brief.

Task given to the author: <path to PROMPT.md>. Solution: <working tree>. Report: <REPORT.md>. Clean base: <how to get it>.

1. Review against the task: does each requirement hold; what happens on the failure paths; prove important defects with a probe in your scratch copy. Each defect: severity, file:line, scenario, CONFIRMED or PLAUSIBLE. Skip style.
2. Tests: do the new tests fail on the base and pass on the solution, and do they cover the real scenarios?
3. Check the report's claims: true or false, with evidence.
4. Score 0–10 with sub-scores you fix before reading the solution; deduct for regressions and state them.

Build any fact list you give the grader from the data, never from one arm's report: that favours the arm.
