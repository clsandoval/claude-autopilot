# Autopilot TUI — Design Spec

## Problem

Managing Managed Agent sessions through `/autopilot status` in Claude Code is clunky:
- One session at a time, no overview
- Must manually invoke slash command to check each session
- Questions get missed (the status bug we fixed earlier)
- No live feed of what the agent is doing
- No persistent dashboard to leave open

## Solution

A terminal UI (TUI) dashboard for monitoring and interacting with autopilot sessions. Read-only session management — no session creation (that stays in the plugin via `/autopilot`). The TUI is a companion you leave open in a terminal while working.

## Scope

**In scope:**
- List all sessions for the configured environment
- Monitor session progress (phases, decisions, artifacts, usage)
- Live event stream per session
- Answer `ask_user` questions inline
- Terminate sessions
- Auto-detect blocked sessions and surface questions

**Out of scope:**
- Session creation / dispatch (stays in plugin)
- Skill upload or agent configuration
- Git operations (viewing branches, diffs, PRs)
- Dark mode (light mode only for v1)

## Architecture

Single Python package in `cli/` within the plugin repo.

```
cli/
├── pyproject.toml
└── src/autopilot_tui/
    ├── __init__.py
    ├── app.py              # Textual app — layout, keybindings, polling
    ├── api.py              # Managed Agents REST client
    ├── widgets/
    │   ├── session_list.py # left panel — session list
    │   ├── progress.py     # right-top tab — phase tracker, decisions, usage
    │   ├── artifacts.py    # right-top tab — files committed by agent
    │   ├── question.py     # right-top tab — ask_user question + answer input
    │   └── events.py       # right-bottom — live event log
    └── theme.py            # Claude light-mode CSS
```

### Entry point

```bash
# Install
cd cli && pip install -e .

# Run
autopilot-tui
# or
python -m autopilot_tui
```

Reads `ANTHROPIC_API_KEY` from environment. Reads environment ID from `~/.autopilot/config.json` or `.superpowers/autopilot-config.json` in the current directory. Errors with a clear message if either is missing.

### Layout

3-panel split:
- **Left (34%):** Session list — all sessions for the environment
- **Right-top (66%, flex):** Tabbed view — Progress / Artifacts / Question
- **Right-bottom (66%, 210px):** Event stream + input bar

### Data Flow

1. On startup: `GET /v1/sessions` to list all sessions for the environment
2. When a session is selected: `GET /v1/sessions/{id}/events` to load full event history
3. Poll active session every 5 seconds
4. Parse events into:
   - Phase progress (from `agent.message` text matching `## Phase N`)
   - Decisions (from lines starting with `Decision:`)
   - Artifacts (from `agent.tool_use` where name is `write`)
   - Questions (from `agent.custom_tool_use` where name is `ask_user`)
5. Detect blocked state: check if latest status event is `session.status_idle` with `stop_reason.type == "requires_action"` AND no `session.status_running` after it

### Session List (Left Panel)

Displays all sessions sorted by: blocked first, then running, then complete, then by recency.

Each entry shows:
- Session name/slug
- Status indicator: `● running` / `◆ blocked` / `✓ done` / `✕ error`
- Time since start/last update
- Current phase summary

Selected session has a left border accent and highlighted background.

### Progress Tab (Right-Top)

Shows for the selected session:
- **Phase tracker:** Checklist of phases with status (✓ complete, ◉ in progress, ○ pending) and duration
- **Decisions section:** List of decisions extracted from agent messages
- **Usage section:** Active seconds, output tokens, estimated cost

### Artifacts Tab (Right-Top)

Lists files the agent has written/committed:
- File path and timestamp
- Parsed from `agent.tool_use` events with `name == "write"`
- v1: list only, no preview

### Question Tab (Right-Top)

**Auto-activates** when the selected session has `stop_reason.type == "requires_action"`.

Shows:
- Question text
- Context text
- Multiple choice options (if provided) as selectable cards
- Free-form input at the bottom

**Answering:** User presses `a/b/c` for quick select or types a free-form response. On submit:
1. `POST /v1/sessions/{id}/events` with `user.custom_tool_result` payload
2. Tab switches back to Progress
3. Session resumes polling

### Events Panel (Right-Bottom)

Scrollable log of session events, newest at bottom:
- Tool calls: file reads, bash commands
- Agent messages (truncated)
- Phase transitions (highlighted in green)
- Questions (highlighted in orange)
- Timestamps in HH:MM format

Input bar at bottom for answering questions (focus moves here when Question tab is active).

### Keybindings

| Key | Action |
|-----|--------|
| `↑↓` | Navigate session list |
| `enter` | Select session |
| `tab` | Cycle focus between panels |
| `d` | Terminate selected session (with confirmation) |
| `1/2/3` | Switch right-top tab: Progress / Artifacts / Question |
| `a/b/c` | Quick-answer multiple choice (Question tab active) |
| `r` | Force refresh |
| `q` | Quit |

### Polling Strategy

- Selected + running session: poll every 5s
- Selected + idle session: no polling (manual refresh with `r`)
- Unselected sessions: refresh list every 30s (status only, not full events)
- Track last seen event ID to avoid re-processing

### Theme — Claude Light Mode

```
Background:     #FAF7F2  (cream)
Surface:        #F0EBE3  (warm gray)
Border:         #E5DFD6  (light border)
Text primary:   #2D2B28  (near black)
Text secondary: #6B6560  (medium gray)
Text muted:     #A89F95  (light gray)
Text disabled:  #BDB5AB  (very light)
Accent:         #C17A4A  (Claude tan)
Warning:        #D4874A  (warm orange)
Success:        #7D9B76  (sage green)
```

### API Client

Thin wrapper around the REST API. All calls use:
```
x-api-key: $ANTHROPIC_API_KEY
anthropic-version: 2023-06-01
anthropic-beta: managed-agents-2026-04-01
```

Methods:
- `list_sessions(environment_id)` → session list
- `get_session(session_id)` → session detail
- `get_events(session_id, after_event_id=None)` → events (incremental)
- `send_tool_result(session_id, event_id, content)` → answer question
- `delete_session(session_id)` → terminate

### Dependencies

- `textual>=3.0` — TUI framework
- `httpx` — async HTTP client (Textual is async-native)
- No other runtime dependencies

### Install

```toml
[project]
name = "autopilot-tui"
version = "0.1.0"
requires-python = ">=3.11"
dependencies = ["textual>=3.0", "httpx>=0.27"]

[project.scripts]
autopilot-tui = "autopilot_tui.app:main"
```
