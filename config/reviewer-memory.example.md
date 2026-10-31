# Failure classes from real incidents and confirmed bugs

Copy to `~/.claude/agent-memory/critical-reviewer/MEMORY.md`. Mine lists each class with one real case; the cases are left out here. Replace them with your own.

Check each change against these. Each line: class, then one real case.

- **Foreign fill taken as our own.** A process books another process's action as its own and removes its protection.
- **Duplicate entry through copies.** A venue refuses a duplicate id only while the twin is unfinished, so copies can double up.
- **Safety margin thinner than one price step.** A margin that looks safe in percent is smaller than one step on a cheap symbol.
- **Clock from the wrong event.** A timer starts at watch start, not at the event, and misses the first data.
- **Retries run out with no exit left.** The fallback was already replaced, so nothing closes the position after the last retry.
- **A partial fill ends the retry.** Part of the size counts as done, and the rest stays open with no watch.
- **A loop outlives its position.** A recheck hits a later position or another process's.
- **Absent rows.** A path ends with no record, and a watcher stays silent.
- **Unknown result treated as known.** A lost response or a failed read is not "no order".
- **Two exits fire on one position.** Every exit path needs a guard against the one that already fired.
- **State shared between goroutines.** A copy of a struct still shares its slices.
- **Float error crosses a step.** 50 × 1.1 = 55.000000000000007, so ceil gives 55.01. Check rounding with real prices and steps.
- **Namesake.** A lookup by name picks another item with the same name. Resolve only among the places that list it.
