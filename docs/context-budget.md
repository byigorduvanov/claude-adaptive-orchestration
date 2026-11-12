# Context budget: what loads before the first message

Measured 2026-11-11 on Claude Code 2.1.322 in the desktop app (Code tab), from the
session transcript: the first request cost about 88k tokens, about 82k of it before
the user's own text. That baseline is re-read from cache on every turn and tool call.

| Part | ~tokens |
|---|---|
| Tool schemas (48 tools) | 53k |
| – `Artifact` alone | 17k |
| – built-in browser (13 tools) | 9k |
| – plugin/skill suggestion tools, `ScheduleWakeup`, `SendUserFile`, `ReportFindings` | 7k |
| App system prompt | 10k |
| Skill listing (104 skills) | 8.6k |
| `CLAUDE.md` + memory index | 5.6k |
| Memory plugin (start block + MCP instructions) | 2.8k |

Token numbers are estimates from character counts (about 3.5 chars per token).

## What was changed

In `~/.claude/settings.json`:

```json
{
  "env": { "CLAUDE_CODE_DISABLE_ARTIFACT": "1" },
  "permissions": {
    "deny": ["SearchPlugins", "SuggestPluginInstall", "SuggestSkills",
             "ReportFindings", "SendUserFile", "ScheduleWakeup"]
  },
  "skillOverrides": { "<rarely-used-skill>": "name-only" }
}
```

- A bare tool name in `permissions.deny` removes the tool from context.
- `skillOverrides` does not apply to plugin skills (`plugin:skill` keys do nothing);
  the only lever there is disabling the plugin.
- When the skill listing exceeds its budget (1% of the context window), descriptions
  are dropped starting with the least used skills, so unused skills cost triggers of
  the used ones.
- App side: prompt suggestions off (each one is an extra model request), unused
  claude.ai connectors off, browser tools off when not needed.
- The memory index keeps only owner rules and topic indexes; dated notes live in
  topic index files.
- `CLAUDE.md` went from 13.7k to 8.8k characters: every rule kept, benchmark numbers,
  incident stories and long example lists removed.


## Second measurement and pass (2026-11-12)

First request of a new session after the changes above (Claude Code 2.1.321, desktop app,
from the transcript's `usage`): **48,226 tokens** (input 2 + cache_creation 24,204 +
cache_read 24,020), down from 88k (−45%). Split by character share (~2.8 chars/token here):

| Part | ~tokens | chars now / before |
|---|---|---|
| Tool schemas (20 tools) | 15.5k | 43k / ~185k |
| App system prompt | 10.2k | 29k / ~35k |
| Skill listing (103 skills) | 10.7k | 30k / ~30k |
| `CLAUDE.md` + memory index | 5.0k | 14k / ~20k |
| Memory plugin | 1.9k | 5.2k / ~9.8k |
| Agent types + deferred tool names | 3.0k | 8.4k |

Usage over 30 days (90 sessions) showed 17 of 103 skills invoked and several app tools
almost never called. Second pass, each step checked in a fresh probe session (a new app
session told to answer `ok`, then its first `usage` and `api-request-shape` read from the
transcript):

| Probe | First request | Change |
|---|---|---|
| Before second pass | 48,226 | — |
| Denies + shorter descriptions + `name-only` | 45,758 | only `Workflow` left the tool list |
| + `skillListingMaxDescChars: 300` | **44,013** | skill listing 31.9k → 24.9k chars |
| + `setup-self-improve` cut, new `claude-context-budget-probe` skill | 45,086 | listing 23.6k chars; +3.6k chars claude-mem MCP instructions that had not connected yet in probe 2 |

Probe-to-probe noise: whether the claude-mem MCP server has connected before the first
request changes the total by ~1.3k tokens (MCP instructions + deferred tool names). Compare
components with `measure.py --compare`, not only totals.

The procedure and script are the `claude-context-budget-probe` skill in this repo.

Findings:

- `permissions.deny` removes CLI tools (`Workflow` worked) but **not** the tools the desktop
  app injects (`mcp__ccd_*`, `mcp__visualize__*`, `mcp__terminal__*`), not even with a
  server-level rule like `mcp__visualize`. No app setting turns them off either.
- The skill listing has a fixed budget (`skillListingBudgetFraction`, default 1% of the
  window). Shortening our own descriptions did not shrink it: the freed space was refilled
  with the full descriptions of plugin skills (`anthropic-skills:*`, `claude-mem:*`) that
  had been name-only before. What does shrink it is `skillListingMaxDescChars` (per-skill
  cap, default 1536); 300 fits every rewritten description.
- Kept: `Workflow` deny (re-enable for ultracode), 29 descriptions cut to ~220–280 chars,
  seven research skills `name-only`.
- Still large and fixed: app system prompt (~31k chars) and app-injected tools.
- The task-contract hook adds ~0.5k tokens to every user message, not once per session.
