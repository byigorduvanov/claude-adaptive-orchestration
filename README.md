# Adaptive orchestration for Claude Code

Rules that let the main Claude session decide, task by task, whether to work alone or build a team of subagents, plus a guard hook and the kit used to measure the result.

There is no fixed pipeline. The session answers three questions and attaches only what the answers call for:

1. What would prove this is done?
2. What can run at once?
3. What is expensive to get wrong?

**This is not proven to beat one plain session.** On small tasks in our runs it took about twice as long, scored higher on a money-path fix, and no better on a data triage. Parallel agents clearly helped only on a broad audit. Each number is one run: see [docs/RESULTS.md](docs/RESULTS.md).

## What's here

| Path | What it is |
|---|---|
| [`config/CLAUDE.orchestration.md`](config/CLAUDE.orchestration.md) | The rules, to paste into `CLAUDE.md` |
| [`agents/`](agents/) | `scout`, `reviewer`, `critical-reviewer`, `verifier` |
| [`hooks/guard-bash.py`](hooks/guard-bash.py) | Blocks unapproved force pushes, staging everything in shared checkouts, and listed hosts |
| [`benchmark/`](benchmark/) | Compare two configs on your own tasks, grade them, classify past sessions |
| [`docs/`](docs/) | Results and sources |

## Install

```bash
git clone https://github.com/byigorduvanov/claude-adaptive-orchestration
cd claude-adaptive-orchestration
mkdir -p ~/.claude/agents ~/.claude/hooks
cp agents/*.md ~/.claude/agents/
cp hooks/guard-bash.py ~/.claude/hooks/
chmod +x ~/.claude/hooks/guard-bash.py
cp hooks/guard-bash.example.json ~/.claude/hooks/guard-bash.json
```

1. Edit `~/.claude/hooks/guard-bash.json` with your own shared checkouts and blocked hosts.
2. Add the `hooks` block from `config/settings.example.json` to `~/.claude/settings.json`, keeping the settings you have.
3. Paste `config/CLAUDE.orchestration.md` into `~/.claude/CLAUDE.md`, then keep the task table to what fits your work.

Back up those files first. New sessions pick up `CLAUDE.md`. `critical-reviewer` is generic: add your own failure modes to it.

```bash
python3 tests/test_guard.py
```

## About the guard

It stops accidents, not a determined agent: the session can set `OWNER_APPROVED_FORCE_PUSH=1` itself, and a differently written command can get past the text matching. It fails open on any error. It uses `deny` because, in our test under `bypassPermissions`, an `ask` decision did not stop the command.

## Benchmark

```bash
# run both scripts from the directory the task works in; KIT is your clone of this repo
AB=~/ab OLD_CONFIG=~/old-config NEW_CONFIG=~/.claude TASKS="fix triage" zsh $KIT/benchmark/setup_arms.sh
# write ~/ab/<task>/PROMPT.md with {X} for the arm, then:
AB=~/ab zsh $KIT/benchmark/run_arm.sh fix a
AB=~/ab python3 $KIT/benchmark/score.py fix a b
```

macOS and zsh; `cp -c` needs APFS. Runs use your Claude plan or API usage: an Opus run here took 12–36 minutes. `benchmark/grader_brief_template.md` and `classify_brief.md` are prompts to adapt. Grade every arm with the same brief.

## Українською

Правила для Claude Code: основна сесія сама вирішує під кожну задачу, працювати самій чи зібрати команду агентів. Хук блокує випадковий force-push. Поруч лежить кит для порівняння конфігурацій. Те, що схема краща за звичайну сесію, не доведено: чесні цифри в [docs/RESULTS.md](docs/RESULTS.md).

## License

MIT
