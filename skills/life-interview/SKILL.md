---
name: life-interview
description: Run one day of the week-long interview that fills the owner's personal vault — pick the next life area (profile, work, money, health, people, home/travel/documents, goals), ask about its open topics, write every answer straight into the right vault file as a dated, sourced fact, and tick the checklist. Use whenever the owner says "давай інтерв'ю", "продовжимо інтерв'ю", "постав мені питання", "розпитай мене", "день 3", "що ще не покрито", "interview me", "next interview day", or starts answering questions about their own life in the assistant folder. Use it instead of asking ad-hoc questions: it knows what was already covered.
---

# Life interview

The vault is only useful if it holds what the owner would otherwise have to repeat. This interview collects that over a week, one area a day, so no single sitting gets tiring. Two things make it work: answers land in files at once (a session that ends early loses nothing), and a checklist records what is covered (the next day starts where this one stopped, with no repeated questions).

## 1. See where the interview stands

```bash
python3 .claude/skills/life-interview/scripts/interview.py status vault
```

It prints the day to do next, the file that day writes to, and its open topics with their ids, plus topics left open on a day already started: offer those at the start ("last time we postponed paperwork, now or later?"). If the owner names a day or an area, use that one: add `--day N`. If the vault has no `log/interview-checklist.md` yet, copy `assets/checklist.md` there first.

Read the target file and `vault/index.md` before asking anything, and skip what the vault already answers.

## 2. Ask

- One area per day. When the day's topics are done, stop and say what tomorrow covers, even if the owner has energy left: a short session that happens seven times beats a long one that happens once. If the owner asks to go on, go on.
- Ask one topic at a time, as two to four plain questions in one message, in the owner's language. Free text, not multiple choice: the owner often dictates by voice, and a long rambling answer carries more than a picked option.
- Follow up once where an answer is vague and the detail will matter for a real task later ("which airline do you avoid, and why?"). Do not interrogate.
- "Skip", "later" and "don't want to say" are answers. "Later" leaves the topic open and goes into the day's log; "never" closes it with `tick vault <id> --skipped`. Either way, move on.
- Never ask for passwords, PINs, card numbers, CVV or seed phrases. If one is offered, do not write it down; record where it is kept instead.

## 3. Write each answer before asking the next topic

Each fact is one bullet in the day's file, in the owner's words and language, ending with the date and source:

```markdown
## Квитки
- Літає економом, місце біля проходу, без нічних рейсів (2026-11-18, interview)
- Картка лояльності авіакомпанії: зберігається в менеджері паролів, запис "Miles" (2026-11-18, interview)
```

- Today's absolute date, never "today" or "next week" inside the vault. Turn the owner's relative dates into absolute ones ("last spring" → "spring 2026").
- Split a long answer into separate facts; one bullet, one fact. Keep what was said, do not add inferences. An assumption you could not help making goes in as a question to ask, not as a fact.
- A person the assistant may later have to contact, mention or book for (family, a landlord, an accountant) gets their own file `people/<first-last>.md`, even when named in passing; link it from the fact as `[[people/<first-last>]]`. It needs frontmatter (`name`, `description`, `type: person`) and a line in `people/index-people.md`. A document or link facts were taken from gets `sources/<date>-<what>.md` and a line in `sources/index-sources.md`.
- A fact that contradicts one already in the file: put the new one in place and move the old one under `## History` with its original date.
- Any other new file needs frontmatter and a line in `vault/index.md`, or nothing will ever find it.

Then tick the topic, naming the file the answer went to:

```bash
python3 .claude/skills/life-interview/scripts/interview.py tick vault d6-tickets areas/home-travel-documents.md
```

The script refuses to tick when that file holds no fact dated today, which is the check that the answer was really saved.

## 4. Close the day

1. Append to `vault/log/<today>.md` (create it with frontmatter `name: log-<today>`, `description`, `type: log`): which area, which topics were covered, which stay open, each as a bullet ending `(<today>, interview)`.
2. Run the lint; it must print `errors=0`. Fix what it reports (a bullet with no date and source, a note no index links to, a secret that slipped in):
   ```bash
   python3 ~/.claude/skills/memory-staleness-audit/scripts/memory_lint.py vault
   ```
3. Tell the owner in three lines: what was written and where, what stays open, what the next day covers.

## The seven days

| Day | Area | File |
|---|---|---|
| 1 | Profile: identity, location, languages, documents | `profile/basics.md` |
| 2 | Work: jobs, projects, income, schedule | `areas/work.md` |
| 3 | Money: accounts, regular payments, budget rules | `areas/money.md` |
| 4 | Health and routine | `areas/health.md` |
| 5 | People: family, friends, colleagues | `people/*.md` |
| 6 | Home, travel, documents | `areas/home-travel-documents.md` |
| 7 | Goals, values, what the assistant may decide alone | `areas/goals.md` |

The topics of each day live in the checklist, not here: add a line there (`- [ ] dN-short-id: what to ask`) when the owner wants something else covered, and the next run picks it up.
