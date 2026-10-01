---
name: todo-txt-kbtd
description: >-
  Teaches how to read, query, and edit a todo.txt task file using the conventions the KBTD kanban
  board (https://github.com/randogoth/kanban-todo.txt) understands: line anatomy, @context columns,
  +project filters, #hashtag chips, and pter-compatible due/t/id/tracking/spent/pri tags. Use this
  skill for any task-management request against a todo.txt file, including adding, completing,
  reprioritizing, moving, time-tracking, or answering questions like "what's overdue", "what's in
  @work", or "what's untagged", not just hand-editing lines. Install by copying this file into a
  project's skill directory (e.g. .claude/skills/todo-txt-kbtd/SKILL.md) to make any todo.txt there
  KBTD-compatible.
---

# Managing a KBTD-compatible todo.txt

[KBTD](https://github.com/randogoth/kanban-todo.txt) is a single-file kanban board that
renders a `todo.txt` file directly. There's no database, no separate task store. Every card on the
board is one line in the file, and every drag, checkbox, or edit on the board is a one-line rewrite of
it. Editing the file by hand (or as an agent) is exactly equivalent to using the UI, as long as each
line stays parseable in the way described below. This skill is that format contract, plus the
task-management operations built on top of it, so you can act on things like "add a task," "what's
overdue," or "start the timer on this" correctly, not just avoid breaking the file.

It's a close cousin of the standard [todo.txt](https://github.com/todotxt/todo.txt) format, with a few
specific choices worth knowing up front:

- **`@context` picks the board column**, and `+project` is a filter across the whole board, not a
  separate board. This follows [kanto](https://hg.sr.ht/~ser/kanto)'s mapping, not vanilla todo.txt.
- **Completed tasks keep their priority as a `pri:A` tag**, not as a `(A)` prefix. This follows
  [pter](https://codeberg.org/pter/pter)'s convention, and is the detail people most often get wrong
  when hand-editing.
- A board needs no setup beyond the file existing (even empty). There's no header, no schema, no
  per-project initialization. If a repo doesn't have one yet and the user wants one, `touch todo.txt`
  (or any filename they prefer) is enough to start.

## Line anatomy

```
[x] [completion-date] [(priority)] [creation-date] <body>
```

- `x `: literal lowercase `x` + space, present only on completed tasks, followed by the completion date.
- `(A)`–`(Z)`: priority, prefix form. **Only valid on an incomplete task.** A completed task's priority
  lives in the body as `pri:A` instead (see below). The parser is tolerant of a stray `(A)` after `x`
  on read, but never write it that way.
- Dates are `YYYY-MM-DD`.
- `<body>` is everything else: free text that may contain `+project`, `@context`, `#hashtag`, and any
  number of `key:value` tags, in any order, anywhere in the text. They're not separate fields, they're
  just substrings of the body that the board's regexes pick out when rendering.

Four real examples, each a complete, valid line:

```
Buy milk @errands
(A) Write RFC +website @backlog due:2026-11-01
Fix flaky test +app @inprogress #testing id:T12
x 2026-10-01 2026-09-20 Design mockups +website @inprogress pri:B
```

The last one: completed (`x`), completed 2026-10-01, created 2026-09-20, priority B lives in `pri:B`
inside the body, not as a `(B)` prefix.

## The one rule that matters most: edit the body as text, don't reconstruct it

The body is never re-serialized from parsed parts. It's kept as a raw string, and tags are added,
replaced, or removed as narrow string edits in place. If you parse out `+project`, `@context`, etc.
into separate fields and then rebuild the body from those fields, you will silently destroy the user's
own spacing, word order, untagged notes, and any tags you didn't bother to parse. Always work by
locating the exact substring to change and editing around it, not by regenerating the line.

Concretely:

- **Adding a tag that isn't present**: append `key:value` (with one leading space) to the end of the
  body, after trimming trailing whitespace.
- **Updating a tag that's already present**: replace just that `key:value` token in place, same
  position, rest of the line untouched. Never append a second copy. A task with `due:2026-01-01
  due:2026-02-01` is a bug, not a correction.
- **Removing a tag**: delete the token and the one whitespace run immediately before it, so you don't
  leave a double space.
- Tag matching is key-bounded (`\bkey:\S+`), so `due:` won't falsely match inside `overdue:` or
  similar, but by the same logic, don't introduce a new tag whose key is a substring of an existing
  word right before it.

## How the file maps onto the board

| In the file | On the board |
|---|---|
| `@context` | The task's column. **Only the first `@context` token counts.** If a task has more than one, the rest are just shown as extra chips on the card, they don't duplicate it into other columns. A task with no `@context` at all lands in a virtual `Queue` column. |
| `+project` | A filter chip. The header's project filter is multi-select and OR's across whatever's checked. A task with any matching `+project` passes. A task can carry more than one, each shows as its own chip. This is a filter over one board, not a way to create separate boards. |
| `#hashtag` | Shown as a chip, same row as the `+project` chips. Purely cosmetic/organizational, not used for filtering or columns. |
| `(A)`/`pri:A` | Sort order within a column: `(A)` → `(Z)`, unprioritized last, ties broken by original line order in the file. Dragging a card vertically on the board is literally a rewrite of this value. |
| any other `key:value` | Shown as a plain chip if it isn't one of the recognized pter tags below. |
| blank lines | Preserved in the file, but are not tasks and never shown on the board. Don't collapse or reorder them when editing other lines. |

## Metadata tags (pter-compatible)

| Tag | Format | Meaning |
|---|---|---|
| `due:` | `YYYY-MM-DD` | Due-date badge, colored when overdue or due today. Purely informational, does **not** affect sort order (only priority does). |
| `t:` | `YYYY-MM-DD` | Threshold/defer date. A future `t:` dims the card and shows a "starts" badge. It's still on the board (just visually deferred), not hidden, unless the user has toggled "Show deferred" off. |
| `id:` | `<prefix><int>`, e.g. `T12` | A stable identifier. Only assign one if asked to, don't invent IDs proactively. If you need a fresh one, use one more than the highest existing numeric suffix sharing the same prefix. |
| `tracking:` | `YYYY-MM-DD-HH-MM-SS` (local time) | Presence means a time-tracking clock is currently running on this task. Don't add this unless the user is actually starting a timer, it's a live state, not a label. |
| `spent:` | `<N>h<N>m`, e.g. `2h15m`, `45m`, `3h` | Accumulated tracked time. Omit the zero component (`3h`, not `3h0m`). |
| `pri:` | `A`–`Z` | Priority, but **only on completed tasks**, see "Line anatomy" above. Never write `pri:` on an incomplete task, use the `(A)` prefix instead. |

## Making edits

**Add a new task.** Append a new line at the end of the file (trim any trailing blank lines first, so
you don't leave a gap). Don't invent a creation date, todo.txt only gets one if the user supplies it
or asks for it. Give it whatever `@context`/`+project`/tags are relevant so it lands in the right
column from the start.

**Mark a task complete.** Three changes, together:
1. Prefix the line with `x <today's date> ` (date format `YYYY-MM-DD`).
2. If the task had a `(A)` priority prefix, remove it and add `pri:A` to the body instead. Don't just
   leave the `(A)` prefix in place, it's only valid on incomplete tasks.
3. Leave `@context`/`+project`/every other tag untouched.

**Mark a task incomplete again.** Reverse of the above: drop the `x <date> ` prefix. If the body has a
`pri:A` tag, remove it and restore it as a `(A)` prefix instead.

**Change priority on an incomplete task.** Just add/replace/remove the `(A)` prefix. Nothing else
changes.

**Change priority on a completed task.** Add/replace/remove the `pri:A` tag in the body, same as any
other tag (see "the one rule" above). The prefix stays untouched (no priority letter there).

**Move a task to a different column.** Replace the *first* `@context` token with the new one (or
append one if there wasn't any, e.g. moving a `Queue` task into a real column). Leave any additional
`@context` tokens alone.

**Start a time-tracking clock.** Add `tracking:<now>` in the local format `YYYY-MM-DD-HH-MM-SS`. Only
one task is normally tracked at a time, but nothing in the format enforces that. If the user asks to
track a second task, that's their call, not something to silently prevent.

**Stop a time-tracking clock.** Compute elapsed minutes from `tracking:` to now, add that to whatever
`spent:` already holds (0 if absent), remove `tracking:`, and write the new total as `spent:` in
`<N>h<N>m` form. Don't just remove `tracking:` without folding the time into `spent:`, that silently
discards the session.

**Add/remove a project, hashtag, or custom tag.** Same in-place edit as any other tag, see "the one
rule that matters most" above.

## Answering questions about the task list

Agents are often asked things in plain language rather than told exactly what to edit. Map these onto
the file directly, don't guess at a UI that isn't there:

- **"What's overdue / due today / due this week?"** Read every task's `due:` tag and compare the
  `YYYY-MM-DD` string lexically against today's date (ISO dates sort correctly as plain strings, no
  date parsing needed). Overdue means `due:` < today, due today means `due:` == today.
- **"What's deferred / not ready yet?"** Tasks with a `t:` tag whose date is after today.
- **"What's in @work / +project-x?"** Substring match on the relevant `@context` or `+project` token.
  Remember a task can carry more than one `@context`, but only the *first* one determines its column.
- **"What's untagged / unprioritized?"** Tasks with no `(A)`–`(Z)` prefix and, if completed, no
  `pri:` tag.
- **"What am I tracking right now?"** Tasks whose body currently contains a `tracking:` tag.
- **"How much time have I spent on X?"** The `spent:` tag, plus elapsed time since `tracking:` if a
  clock is currently running on it.
- Always read straight from the file for these. It's the single source of truth, and there's no
  cached or derived state anywhere else to consult.

## Common mistakes to avoid

- Writing `pri:` on an incomplete task, or a `(A)` prefix on a completed one. Pick the one that
  matches the task's completion state.
- Rebuilding the whole line from scratch instead of editing the existing text. This loses whatever
  you didn't bother to parse (stray notes, unfamiliar tags, exact spacing).
- Duplicating a tag instead of replacing it in place.
- Touching lines you weren't asked to change. Every board action in KBTD is a single-line rewrite,
  match that. Don't reflow or reorder unrelated lines "while you're in there."
- Deleting or collapsing blank lines. They're part of the file's own formatting, not noise.
- Stopping a tracking clock by just deleting `tracking:` without folding the elapsed time into `spent:`.
- Assuming `due:` affects sort order. It doesn't, only priority does.

## Seeing it on the board

None of the above requires KBTD itself. Plain text edits are the real interface, and this skill works
in any project with a todo.txt file whether or not the board is installed. If the user wants to
visually check the result and `kbtd.py` isn't already available, it's a single self-contained script:

```bash
curl -O https://raw.githubusercontent.com/randogoth/kanban-todo.txt/main/kbtd.py
chmod 755 kbtd.py
./kbtd.py path/to/todo.txt
```

(Requires [uv](https://docs.astral.sh/uv/getting-started/installation/).) That's a nice sanity check
after a batch of edits, not a required step for managing tasks.
