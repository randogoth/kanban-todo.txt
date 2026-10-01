# Kanban-TODO.TXT

[![fork of chr15m/kanban-todo](https://img.shields.io/badge/fork%20of-chr15m%2Fkanban--todo-black?logo=github&logoColor=white)](https://github.com/chr15m/kanban-todo)
[![todo.txt](https://img.shields.io/badge/format-todo.txt-green)](https://github.com/todotxt/todo.txt)
[![Python 3.9+](https://img.shields.io/badge/python-3.9%2B-3776AB?logo=python&logoColor=white)](https://www.python.org/)
[![AI-DECLARATION: copilot](https://img.shields.io/badge/䷼%20AI--DECLARATION-copilot-fee2e2?labelColor=fee2e2)](https://ai-declaration.md)

A [todo.txt](https://github.com/todotxt/todo.txt) based kanban board in a single [index.html](./index.html) file.

[Download index.html](https://code.randogoth.com/randogoth/kanban-todo.txt/raw/branch/main/index.html) | [Download Zip](https://code.randogoth.com/randogoth/kanban-todo.txt/archive/main.zip)

- Drag-and-drop visual editing of a plain text todo.txt file
- Compatible with the wider todo.txt ecosystem: [kanto](https://hg.sr.ht/~ser/kanto)'s board mapping, [pter](https://codeberg.org/pter/pter)'s metadata tags
- Runs 100% in your browser - no server, no database
- Single HTML file - simply upload to self-host
- CLI tool to launch as an app window in any browser (Chrome, Firefox, Safari): `kbtd.py todo.txt`
- Two-way binding between UI and text file
- Great for indie-scale solo projects and small teams

[File format](#file-format) | [CLI Install](#cli-install) | [Agent Skill](#agent-skill) | [Self Host](#self-host) | [Browser Support](#browser-support)

## File Format

The text based format is designed to be simple for humans, git, LLMs, and other todo.txt tools to read and edit. `@context` tags become columns, `+project` tags become filters, and the usual todo.txt metadata tags (`due:`, `t:`, `id:`, `tracking:`, `spent:`) show up as badges on the card.

```
(A) Task number one. +project @column
Some other task. +project @column due:2026-11-01

Yet another task. +project @another-column
```

## CLI Install

Requires [uv](https://docs.astral.sh/uv/getting-started/installation/).

```
curl -O https://code.randogoth.com/randogoth/kanban-todo.txt/raw/branch/main/kbtd.py
chmod 755 kbtd.py

# By default `kbtd.py` loads the web app from my server.
# If self-hosting, set KBTD_URL to load from your server instead:
# export KBTD_URL="https://code.randogoth.com/randogoth/kanban-todo.txt/raw/branch/main/"

# Then launch with:
./kbtd.py todo.txt
```

`kbtd.py` runs a small local server (bound to `127.0.0.1`, guarded by a per-launch token) so the app can read and write your file through any browser, not just Chromium-based ones. It blocks in the foreground for the session: close the browser window or hit Ctrl-C to stop it.

## Agent Skill

[SKILL.md](./SKILL.md) teaches AI coding agents (e.g. Claude Code) how to read, query, and edit a todo.txt file so it stays KBTD-compatible: line format, `@context`/`+project`/`#hashtag` tags, pter metadata tags, priority/completion rules, time tracking. Drop it into any project to make that project's todo.txt agent-manageable:

```
mkdir -p .claude/skills/todo-txt-kbtd
curl -o .claude/skills/todo-txt-kbtd/SKILL.md https://code.randogoth.com/randogoth/kanban-todo.txt/raw/branch/main/SKILL.md
```

## Self Host

Copy `index.html` up to your server.

If you're using the `kbtd.py` command line launcher, set `KBTD_URL` to point at your server.

## Browser Support

Launched via `kbtd.py`, the app works in any browser, including Chrome, Firefox, Safari, and Edge, since `kbtd.py`'s local server handles file access, not the browser.

Without `kbtd.py` (opening `index.html` directly on a static host), the app falls back to the browser's [FileSystem Access API](https://developer.mozilla.org/en-US/docs/Web/API/File_System_Access_API), which only Chromium-based browsers (Chrome, Edge, Brave, etc.) implement. Firefox and Safari don't support this path.

## Copyright

Copyright © [Chris McCormick](https://github.com/chr15m/kanban-todo) 2025 (original idea and Markdown-based app).
todo.txt rewrite and further changes copyright © randogoth 2026.
