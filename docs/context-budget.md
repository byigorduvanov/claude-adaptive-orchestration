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
almost never called. Second pass:

- `permissions.deny` += `Workflow` (re-enable for ultracode), `mcp__visualize__show_widget`,
  `mcp__visualize__read_me`, `mcp__terminal__read_terminal`, `mcp__ccd_session__mark_chapter`,
  `mcp__ccd_session__hand_off_to_session`, `mcp__ccd_session__read_widget_context` (~4k tokens).
- Personal skill descriptions cut from ~450–900 to ~220–280 characters, keeping the main
  Ukrainian trigger phrases (~8k chars, ~3k tokens).
- Seven rarely used research skills set to `name-only` in `skillOverrides`.
- Still large and fixed: app system prompt, app task-list tools (`wrap_up`, `update_plan`).
- The task-contract hook adds ~0.5k tokens to every user message, not once per session.

Not measured yet: the first request of a new session after the second pass.
