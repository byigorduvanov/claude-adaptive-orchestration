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

Not measured yet: the baseline of a new session after these changes.
