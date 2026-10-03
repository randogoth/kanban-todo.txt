# Kanban todo.txt

A minimal Kanban board web app that presents a [todo.txt](https://github.com/todotxt/todo.txt) file as a drag-and-drop board, compatible with the wider todo.txt ecosystem ([kanto](https://hg.sr.ht/~ser/kanto)'s board mapping, and some of [pter](https://codeberg.org/pter/pter)'s metadata tags). The file is the canonical data store: every mutation rewrites one line, and the app re-reads and re-parses the file after every write, so the UI always reflects exactly what's on disk. There is one board per file. Projects are a filter over that single board, not separate boards.

## Core Concepts

| Term | Description |
|------|-------------|
| **Task** | One line in the todo.txt file, draggable between columns |
| **Project** | A `+project` tag on a task: a multi-select filter (OR) over the whole board, plus a `(no project)` entry |
| **Column** | A `@context` tag, derived from the project-filtered task set, ordered by first appearance. Contextless tasks land in a virtual `Queue` column (hidden when empty) |

## todo.txt Format

```
(A) Research competitors +website @backlog
Write RFC +website @backlog due:2026-11-01
x 2026-09-30 2026-09-20 Design mockups +website @inprogress pri:B
Build prototype +website @inprogress
x 2026-09-15 Initial brainstorm +website @done
Something else +app
```

### Parsing Rules

A task line tokenises as `[x] [completion-date] [(priority)] [creation-date] <body>`, tolerant on read of priority appearing either before or after the dates (some todo.txt clients write it differently). The `body` is kept as a raw string and never re-serialised: `+project`, `@context` and `key:value` tags, and the display title, are regex-derived views over it. This preserves the user's own text layout.

- `x ` prefix marks a task complete. The following date is the completion date
- Dates are `YYYY-MM-DD`. A completed task reads `x <completion-date> <creation-date>`, an incomplete one just `<creation-date>`. Both are optional on read, and a lone date on a completed line is the completion date
- `(A)`–`(Z)` is the priority. For a completed task the priority is carried as a `pri:A` tag in the body instead of the prefix
- `+project` and `@context` tags are free text within the body. A task can carry several of each
- `due:`, `t:`, `id:`, `tracking:`, `spent:` are [pter](https://codeberg.org/pter/pter)-compatible metadata tags (see below)
- Blank lines are preserved in the file but are not tasks
- A task's column is its *first* `@context`. Additional contexts are preserved and shown as chips (a multi-context task is rendered once, not duplicated across columns)
- Cards within a column sort `(A)`→`(Z)`, unprioritised last, ties by file order

### Metadata Tags (pter-compatible)

| Tag | Format | Behaviour |
|---|---|---|
| `due:` | `YYYY-MM-DD` | Display badge only, coloured when overdue/today. Does not affect sort order |
| `t:` | `YYYY-MM-DD` | Threshold/defer date. Future-dated cards render dimmed with a "starts" badge. The "Show deferred" toggle controls visibility (defaults to showing) |
| `id:` | `<prefix><int>` | Parsed, displayed and preserved always. Allocated on demand via "Assign ID" |
| `tracking:` | `YYYY-MM-DD-HH-MM-SS` | Presence means the clock is running. Started and stopped via "Start/Stop tracking" |
| `spent:` | `<N>h<N>m` | Accumulated time, updated when tracking stops |

## Architecture

Two components: the `kbtd.py` launcher (resolves the file, finds/launches a browser, runs a loopback HTTP server) and `index.html` (the entire web app).

`index.html` talks to the file through one of two interchangeable backends, selected once at startup by whether a `token` URL parameter is present:

- **`FsaBackend`**: the browser's File System Access API (`showOpenFilePicker`, `FileSystemFileHandle`, permission re-grant on reload). Used when `index.html` is opened directly with no `kbtd.py` (e.g. a self-hosted static copy, bookmarked by the user). Chromium-only. First launch shows a landing page / file picker. A FileSystemFileHandle is then stored in IndexedDB (`kbtd` DB, `fileHandles` store, keyed by file path) so later launches skip straight to a permission check.
- **`HttpBackend`**: talks to `kbtd.py`'s local HTTP server (`GET`/`HEAD`/`PUT /file`) instead of a browser file API. Used whenever the app is launched via `kbtd.py`, in every browser including Chromium, with one code path, no permission screen, and no stored-handle bookkeeping, since each `kbtd.py` launch is already scoped to one file and the server has direct OS-level file access.

### State Management

- **File state**: the todo.txt file is the source of truth for task data
- **UI state**: localStorage, keyed by file path (`kbtd:${filePath}`), stores the project filter and the show-completed/show-deferred/group-completed toggles:
  ```json
  { "projectFilter": ["website"], "showCompleted": true, "showDeferred": true, "groupCompleted": false }
  ```
  `projectFilter: null` means all projects. `(no project)` is a reserved sentinel string, not a real project name.
- **Session-only state**: a column created via "Add column" before any task uses it lives only in memory (`state.pendingLanes`) until a task lands in it, or vanishes on reload

## User Interface

- Columns displayed horizontally, derived from the file (see Parsing Rules), cards sorted by priority within each column
- Drag and drop within a column sets the dragged card's priority letter (inherited from the card *below* the drop point, falling back to the one above at the bottom of a list)
- Drag and drop across columns rewrites the card's `@context` and sets its priority together, in one write
- "Completed column" toggle: pools every completed task into a synthetic rightmost column instead of leaving it in its `@context` lane. Dragging into it marks a card complete, and dragging out marks it incomplete and files it under the target column
- Card face shows title, `+project`/`#hashtag` chips, priority/due/spent/tracking badges, an `id:` chip and chips for any other tags
- Header project filter is a multi-select checklist (OR across selected projects), plus a `(no project)` entry
- New cards are stamped with today's creation date. A card added straight into the synthetic Completed column also gets today's completion date. Completing an existing card adds a completion date and keeps whatever creation date the line already had, no creation date is invented after the fact
- Card menu: Completed, Set project..., Start/Stop tracking, Assign ID, Delete
- Card detail modal: free-text body, priority, due date, start (`t:`) date, spent, start/stop tracking, ID

## File Synchronization

- Polling every 250ms: `FsaBackend` compares `file.lastModified`. `HttpBackend` compares the `/file` endpoint's `ETag` via `HEAD`. On change, reload, re-derive columns, re-render
- Every mutation is a single-line edit. Other lines are never rewritten. `FsaBackend` writes via `FileSystemFileHandle.createWritable()`. `HttpBackend` writes via `PUT /file` with an `If-Match` header carrying the ETag last read
- Conflict resolution: `FsaBackend` has none. Last write wins, external changes blow away app state. `HttpBackend` rejects a stale `If-Match` with `412 Precondition Failed`. The app reloads the latest version from disk and shows a message rather than silently losing the edit

## Launcher (`kbtd.py`)

A single-file Python script, run via `uv run --script` (PEP 723 inline metadata). Its one dependency, `certifi`, is declared inline and resolved automatically by `uv`, with no manual install step. (It's needed because `uv`'s managed Python builds don't reliably see the OS trust store on every platform, notably Nix.)

### Usage

```bash
kbtd.py [OPTIONS] <path-to-todo.txt-file>

Options:
  --browser    Open in existing browser instead of app mode
  --permanent  Reuse a fixed port/token for this file; disables idle shutdown
  --help       Show help message
```

### Behavior

1. Resolve the todo.txt file path to an absolute path, creating it if missing (and its parent directory exists)
2. Load `index.html`: if a copy sits next to `kbtd.py` itself (e.g. a repo checkout), read it directly. Otherwise fetch it from `$KBTD_URL` (default: the public hosted copy, accepts either a directory or a full URL ending in `.html`). Fails with a clear error if unreachable
3. Start a loopback HTTP server on `127.0.0.1` (OS-assigned port), guarded by a per-launch random token, and print its URL. With `--permanent`, reuse the port/token persisted for this file in `~/.config/kbtd/sessions/` instead (creating that session on first use), or detect and reuse an already-running `--permanent` instance for the same file rather than binding a second server
4. Locate a browser (Chromium family, Firefox, or Safari) and launch it pointed at `http://127.0.0.1:{port}/?file={absolute_path}&token={token}`. If none is auto-detected, this is **not fatal**. The server keeps running and the printed URL can be opened manually in any browser
5. Block in the foreground: in `--app` mode (with a detected browser), until that browser window closes. Otherwise, until the server idles out (10 minutes with no `/file` requests, skipped with `--permanent`) or Ctrl-C

### Server Endpoints

| Route | Auth | Behavior |
|---|---|---|
| `GET /` | none | Serves the fetched `index.html` bytes |
| `GET`/`HEAD /file` | `X-Kbtd-Token` header | Returns the file's current bytes and a content-hash `ETag`. `404` if missing |
| `PUT /file` | `X-Kbtd-Token` header, `If-Match` | Writes atomically (temp file + `os.replace`) if `If-Match` matches the current `ETag`. `412` otherwise |

Any other route is `404`. The server never derives a filesystem path from a request. It only ever touches the one path resolved at startup, so there is no path-traversal surface.

### Security Model

Threat model is other local processes/pages on the same machine, not remote attackers:

- Binds `127.0.0.1` only: no network-reachable surface
- Per-launch random token (`secrets.token_urlsafe(24)`) required via the custom header `X-Kbtd-Token` on every `/file` request. A cross-origin page can't attach a custom header without triggering a CORS preflight, which the server fails (no `Access-Control-Allow-Origin`). This also covers DNS-rebinding variants, since the preflight's `Origin` reflects the real page origin regardless of which IP it resolved to
- `GET /` is intentionally unauthenticated (static public markup, also the only route reachable before the token is known, since it arrives in that page's own URL)
- Random OS-assigned port per launch, plus the idle-timeout shutdown, bound the window during which a port-scan-plus-token-guess is relevant
- Not defended against (accepted): another process running as the *same OS user* reading the token from `ps aux` or browser history. The file's absolute path is exposed the same way already, via the URL and the browser's own argv
- `--permanent` is opt-in and trades away the two bullets above: the port and token are persisted per-file in `~/.config/kbtd/sessions/<hash>.json` (`0600`, directory `0700`) and reused across launches instead of regenerated, and the idle-timeout shutdown is skipped. The token becomes a long-lived secret on disk rather than a short-lived in-memory one for the run's duration

### Browser Detection

Auto-detects a Chromium/Firefox/Safari install across `$BROWSER`, `PATH`, macOS app bundles, and WSL. See `find_browser()` in `kbtd.py` for the exact order. Chromium gets an isolated `--app=<url>` window with its own `--user-data-dir`. Firefox/Safari get a plain new window (no isolated-profile app-mode equivalent exists for them).

## Non-Goals

- No task descriptions/subtasks. todo.txt has no convention for them, so indented detail lines are not supported
- No multi-file support
- No offline support beyond what the browser provides
- No collaborative editing
- No mobile support
- `kbtd.py`'s server is local single-user only: no remote/multi-user hosting, no auth beyond the one per-launch token
