# KBTD - Kanban TODO

A minimal Kanban board web app that uses a [todo.txt](https://github.com/todotxt/todo.txt) file as its data store, compatible with the wider todo.txt ecosystem ([kanto](https://hg.sr.ht/~ser/kanto)'s board mapping, [pter](https://codeberg.org/pter/pter)'s metadata tags).

## Overview

KBTD presents a Kanban board interface for managing tasks stored in a standard todo.txt file. The file is the canonical data store — the app provides a visual interface for viewing and manipulating it. There is one board per file; projects are a filter over that single board, not separate boards.

## Core Concepts

| Term | Description |
|------|-------------|
| **Task** | One line in the todo.txt file — draggable between columns |
| **Project** | A `+project` tag on a task — a multi-select filter (OR) over the whole board, plus a `(no project)` entry |
| **Column** | A `@context` tag — derived from the project-filtered task set, ordered by first appearance. Contextless tasks land in a virtual `Queue` column (hidden when empty) |

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

A task line tokenises as `[x] [completion-date] [(priority)] [creation-date] <body>`, tolerant on read of priority appearing either before or after the dates (some todo.txt clients write it differently). The `body` is kept as a raw string and never re-serialised — `+project`, `@context` and `key:value` tags, and the display title, are regex-derived views over it. This preserves the user's own text layout.

- `x ` prefix marks a task complete; the following date is the completion date
- `(A)`–`(Z)` is the priority; for a completed task the priority is carried as a `pri:A` tag in the body instead of the prefix
- `+project` and `@context` tags are free text within the body; a task can carry several of each
- `due:`, `t:`, `id:`, `tracking:`, `spent:` are [pter](https://codeberg.org/pter/pter)-compatible metadata tags (see below)
- Blank lines are preserved in the file but are not tasks
- A task's column is its *first* `@context`; additional contexts are preserved and shown as chips (a multi-context task is rendered once, not duplicated across columns)
- Cards within a column sort `(A)`→`(Z)`, unprioritised last, ties by file order

### Metadata Tags (pter-compatible)

| Tag | Format | Behaviour |
|---|---|---|
| `due:` | `YYYY-MM-DD` | Display badge only, coloured when overdue/today. Does not affect sort order |
| `t:` | `YYYY-MM-DD` | Threshold/defer date. Future-dated cards render dimmed with a "starts" badge; "Show deferred" toggle controls visibility (defaults to showing) |
| `id:` | `<prefix><int>` | Parsed, displayed and preserved always; allocated on demand via "Assign ID" |
| `tracking:` | `YYYY-MM-DD-HH-MM-SS` | Presence means the clock is running; started/stopped via "Start/Stop tracking" |
| `spent:` | `<N>h<N>m` | Accumulated time; updated when tracking stops |

## Architecture

### Components

1. **Shell script (`kbtd`)** - Cross-platform launcher
2. **Single HTML file (`index.html`)** - The entire web application

### Data Flow

```
┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│  todo.txt   │◄───►│  Web App    │◄───►│ localStorage│
│  (file)     │     │  (browser)  │     │ (UI state)  │
└─────────────┘     └─────────────┘     └─────────────┘
      │                    │
      │   File System      │   IndexedDB
      │   Access API       │   (FileHandle)
      │                    │
      └────────────────────┘
```

### State Management

- **File state**: The todo.txt file is the source of truth for task data
- **UI state**: localStorage stores project filter and show-completed/show-deferred toggles, keyed by file path
- **File handle**: IndexedDB stores the FileSystemFileHandle for persistence across sessions
- **Session-only state**: a column created via "Add column" before any task uses it lives only in memory (`state.pendingLanes`) until a task lands in it, or vanishes on reload

#### localStorage Schema

Key: `kbtd:${filePath}`

```json
{
  "projectFilter": ["website"],
  "showCompleted": true,
  "showDeferred": true
}
```

`projectFilter: null` means all projects. A `(no project)` entry in the filter is represented by a reserved sentinel string, not a real project name.

#### IndexedDB Schema

Database: `kbtd`
Object Store: `fileHandles`
Key: file path from URL query string
Value: FileSystemFileHandle

## User Interface

### States

1. **No file associated**: Shows file picker button and instructions
2. **Permission needed**: Shows button to re-grant permission (after page reload)
3. **File not found**: Shows error message if the file doesn't exist
4. **Kanban board**: Shows columns and cards directly — there is no separate board-picker screen

### Kanban Board Features

- Columns displayed horizontally, derived from the file (see Parsing Rules)
- Cards displayed vertically within columns, sorted by priority
- Drag and drop within a column sets the dragged card's priority letter (inherited from its new neighbours)
- Drag and drop across columns rewrites the card's `@context` and sets its priority together, in one write
- Card face shows title, `+project` chips, priority/due/spent/tracking badges, an `id:` chip and chips for any other tags
- Header project filter is a multi-select checklist (OR across selected projects), plus a `(no project)` entry
- Card menu: Completed, Set project..., Start/Stop tracking, Assign ID, Delete
- Card detail modal: free-text body, priority, due date, start (`t:`) date, spent, start/stop tracking, ID

## File Synchronization

### Polling

- Poll file every 250ms using `file.lastModified`
- On change detected: reload file, re-derive columns, re-render UI

### Write Strategy

- Every mutation is a single-line edit via `modifyFileLines`; other lines are never rewritten
- Use `FileSystemFileHandle.createWritable()` for atomic writes
- After every write, the app re-reads and re-parses the file, so the UI always reflects exactly what's on disk

### Conflict Resolution

None. Last write wins. External changes blow away app state.

## Shell Script (`kbtd`)

### Usage

```bash
kbtd [OPTIONS] <path-to-todo.txt-file>

Options:
  --browser    Open in existing browser instead of app mode
  --help       Show help message
```

### Behavior

1. Resolve the todo.txt file path to absolute path
2. Locate a Chromium-based browser (Chrome, Chromium, Edge)
3. Determine mode:
   - Default: `--app` mode with isolated `--user-data-dir` in current directory
   - With `--browser`: open in existing browser instance with `--new-window`
4. Launch browser with URL: `{base_url}?file={absolute_path}`

### Browser Detection

Check in order:
1. `$BROWSER` environment variable (if Chromium-based)
2. `google-chrome` / `chromium` / `chromium-browser` / `microsoft-edge` in PATH
3. macOS: `/Applications/Google Chrome.app/...`, `/Applications/Chromium.app/...`, `/Applications/Microsoft Edge.app/...`
4. WSL: `/mnt/c/Program Files/Google/Chrome/Application/chrome.exe`, etc.

If no Chromium browser found: exit with error message explaining requirement.

### URL Configuration

- Development: `http://localhost:8000`
- Production: Configurable via `$KBTD_URL` environment variable or hardcoded default

## Web App Behavior

### Startup Flow

```
1. Parse ?file= from URL query string
2. If no file param:
   → Show landing page with instructions and script download link
3. Check IndexedDB for stored FileHandle for this file path
4. If handle exists:
   → Check permission with queryPermission()
   → If "granted": proceed to load file
   → If "prompt": show "Grant Access" button
   → If "denied": show file picker
5. If no handle:
   → Show file picker button
6. On file picker success:
   → Store handle in IndexedDB
   → Load and parse file, show board directly
```

### File Picker

```javascript
const [fileHandle] = await window.showOpenFilePicker({
  id: 'kbtd-todo-file',
  mode: 'readwrite',
  types: [{
    description: 'todo.txt files',
    accept: { 'text/plain': ['.txt'] }
  }]
});
```

### Permission Re-grant

After page reload, stored handles return `"prompt"` for permission state. User must click a button to trigger:

```javascript
const permission = await fileHandle.requestPermission({ mode: 'readwrite' });
```

This requires a user gesture (button click).

## Browser Compatibility

**Required**: Chromium-based browser (Chrome 86+, Edge 86+, Opera 72+)

**Not supported**: Firefox, Safari (File System Access API not implemented). See "Out of scope" below for the planned HTTP-backend follow-up that would lift this restriction.

## File Structure

```
kbtd/
├── index.html      # Complete web application (single file)
├── kbtd            # Shell script launcher
└── SPEC.md         # This specification
```

## Architecture Principles

### Source of Truth

The todo.txt file is the **only** source of truth. The Kanban UI is purely a renderer and editor for the file. There is no separate application state that needs to be "synced" with the file.

### Data Flow

```
File Change → Read File → Parse → Derive columns → Render
User Action → Modify one line → Write File → Read File → Parse → Derive columns → Render
```

## Non-Goals

- No task descriptions/subtasks — todo.txt has no convention for them, so indented detail lines are not supported
- No multi-file support
- No offline support beyond what the browser provides
- No collaborative editing
- No mobile support
- No server component (pure client-side) — see "Out of scope" below

## Out of Scope (follow-up change)

The data layer is the File System Access API throughout, which Firefox and Safari don't implement. A planned follow-up gives `kbtd` a loopback HTTP server (`GET /` → index.html, `GET`/`HEAD`/`PUT /file` with ETag + If-Match) and splits index.html's I/O behind a backend interface (`FsaBackend` for today's self-hosted story, `HttpBackend` for Firefox/Safari/mobile), binding 127.0.0.1 on a random port with a per-launch token. Not part of this change.
