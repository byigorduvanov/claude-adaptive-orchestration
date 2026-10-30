# Sources

Read in October 2026.

**Anthropic**
- [When to use multi-agent systems (and when not to)](https://claude.com/blog/building-multi-agent-systems-when-and-how-to-use-them): 3–10× tokens; context protection, parallelization, specialization; split by context, not work type; "The primary benefit of parallelization is thoroughness, not speed."
- [Claude Code best practices](https://code.claude.com/docs/en/best-practices): give Claude a check to run; a fresh reviewer helps, delegating the same task does not; "skip style"; hooks for rules with no exceptions.
- [How we built our multi-agent research system](https://www.anthropic.com/engineering/multi-agent-research-system): +90.2% on a research eval at about 15× tokens; "most coding tasks involve fewer truly parallelizable tasks than research".
- [Multi-agent coordination patterns](https://claude.com/blog/multi-agent-coordination-patterns), [Building effective agents](https://www.anthropic.com/engineering/building-effective-agents), [Sub-agents](https://code.claude.com/docs/en/sub-agents), [Dynamic workflows](https://code.claude.com/docs/en/workflows).

**Others**
- [Cognition: Multi-Agents: What's Actually Working](https://cognition.com/blog/multi-agents-working): "multi-agent systems work best today when writes stay single-threaded"; review with a clean context finds about 2 bugs per PR (vendor's own data).
- [METR, February 2026](https://metr.org/blog/2026-02-24-uplift-update/): measurements are unreliable for developers running several agents at once. No solid measurement of a multi-agent speed-up exists.
