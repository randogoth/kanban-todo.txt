A [todo.txt](https://github.com/todotxt/todo.txt) based kanban board in a single [index.html](./index.html) file.

[Download index.html](https://raw.githubusercontent.com/chr15m/kanban-todo/main/index.html) | [Download Zip](https://github.com/chr15m/kanban-todo/archive/refs/heads/main.zip)

- Drag-and-drop visual editing of a plain text todo.txt file
- Compatible with the wider todo.txt ecosystem — [kanto](https://hg.sr.ht/~ser/kanto)'s board mapping, [pter](https://codeberg.org/pter/pter)'s metadata tags
- Runs 100% in your browser - no server, no database
- Single HTML file - simply upload to self-host
- CLI tool to launch as a Chrome app: `kbtd todo.txt`
- Two-way binding between UI and text file
- Great for indie-scale solo projects and small teams

[File format](#file-format) | [CLI Install](#cli-install) | [Self Host](#self-host) | [Browser Support](#browser-support) | [Video Walkthrough](#video-walkthrough)

![Screencast of TODO Kanban editing a todo.txt file](./screencast.gif)

## File Format

The text based format is designed to be simple for humans, git, LLMs, and other todo.txt tools to read and edit. `@context` tags become columns, `+project` tags become filters, and the usual todo.txt metadata tags (`due:`, `t:`, `id:`, `tracking:`, `spent:`) show up as badges on the card.

```
(A) Task number one. +project @column
Some other task. +project @column due:2026-11-01

Yet another task. +project @another-column
```

## CLI Install

```
curl -O https://mccormick.cx/apps/kanban-todo/kbtd
chmod 755 kbtd

# By default `kbtd` loads the web app from the my server.
# If self-hosting, set KBTD_URL to load from your server instead:
# export KBTD_URL="https://mccormick.cx/apps/kanban-todo/"

# Then launch with:
./kbtd todo.txt
```

## Self Host

Copy `index.html` up to your server.

If you're using the `kbtd` command line launcher, set `KBTD_URL` to point at your server.

## Browser Support

Unfortunately the web app requires a Chromium-based browser (Chrome, Edge, Brave, etc.) for the [FileSystem Access API](https://developer.mozilla.org/en-US/docs/Web/API/File_System_Access_API). Firefox and Safari don't implement it. The `kbtd` script runs the app in an isolated browser instance that doesn't interfere with your main browser.

## Video walkthrough

[![Video walkthrough of Kanban TODO](https://img.youtube.com/vi/yyBZceJG-Ls/maxresdefault.jpg)](https://youtu.be/yyBZceJG-Ls)
