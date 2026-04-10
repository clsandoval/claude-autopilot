# Autopilot TUI — Implementation Plan

## Reference
- Spec: `docs/2026-04-10-autopilot-tui-design.md`

## Task Breakdown

### Task 1: Project scaffold
Create `cli/` directory with `pyproject.toml` and package skeleton:
- `cli/pyproject.toml` — package metadata, dependencies, entry point
- `cli/src/autopilot_tui/__init__.py` — empty init
- Verify package is pip-installable

### Task 2: API client (`api.py`)
Implement `AutopilotAPI` async class with httpx:
- `__init__(api_key, environment_id)`
- `list_sessions()` → list of session dicts
- `get_session(session_id)` → session detail
- `get_events(session_id, after_event_id=None)` → events list
- `send_tool_result(session_id, tool_use_id, content)` → POST answer
- `delete_session(session_id)` → DELETE
- Auth headers: `x-api-key`, `anthropic-version: 2023-06-01`, `anthropic-beta: managed-agents-2026-04-01`

### Task 3: Theme (`theme.py`)
CSS string constant `THEME_CSS` with full light-mode theme:
- Variables for all 9 named colors from spec
- Base widget styling (App background, borders, scrollbars)
- Panel border and surface styles
- Status indicator colors (running/blocked/done/error)

### Task 4: Event parser (`events.py` module-level helpers)
Pure functions to parse raw event lists:
- `extract_phases(events)` → list of `{name, status, started_at, ended_at}`
- `extract_decisions(events)` → list of `{text, timestamp}`
- `extract_artifacts(events)` → list of `{path, timestamp}`
- `extract_question(events)` → `{tool_use_id, question, context, options}` or None
- `is_blocked(events)` → bool — checks latest status event for requires_action
- `format_event_line(event)` → display string for event stream

### Task 5: Session list widget (`widgets/session_list.py`)
`SessionListWidget(Widget)`:
- Renders sorted sessions: blocked → running → complete → error → by recency
- Each row: status dot + name + time-ago + current phase summary
- Selection with highlight and left-border accent
- Emits `SessionSelected(session_id)` message on enter/click
- `update_sessions(sessions)` method to refresh data

### Task 6: Events panel widget (`widgets/events.py`)
`EventStreamWidget(Widget)`:
- Scrollable log, newest at bottom
- Color-coded lines: phase transitions (green), questions (orange), normal (text-secondary)
- Timestamps in HH:MM
- `update_events(events)` method
- Auto-scroll to bottom on new events

### Task 7: Progress tab widget (`widgets/progress.py`)
`ProgressWidget(Widget)`:
- Phase checklist: ✓ / ◉ / ○ with name and duration
- Decisions list with timestamps
- Usage section: active_seconds, output_tokens, cost estimate
- `update(session, events)` method

### Task 8: Artifacts tab widget (`widgets/artifacts.py`)
`ArtifactsWidget(Widget)`:
- Scrollable list of `{path, timestamp}` items
- Empty state message when no artifacts
- `update(artifacts)` method

### Task 9: Question tab widget (`widgets/question.py`)
`QuestionWidget(Widget)`:
- Question text + context display
- Multiple choice option cards (a/b/c labels)
- Free-form text input at bottom
- `load_question(question_data)` method
- Emits `AnswerSubmitted(tool_use_id, answer_text)` message
- `a/b/c` quick-select populates input, submit on enter

### Task 10: Main app (`app.py`)
`AutopilotApp(App)`:
- Config loading: reads `~/.autopilot/config.json` or `.superpowers/autopilot-config.json`
- Layout: horizontal split (34% left / 66% right) with vertical right split (flex top / 210px bottom)
- Tabbed right-top panel: Progress (1) / Artifacts (2) / Question (3)
- Keybindings: ↑↓ navigate, enter select, tab cycle focus, d delete, 1/2/3 tabs, a/b/c quick answer, r refresh, q quit
- Polling: 5s timer for selected+running, 30s timer for session list refresh
- On session select: load events, update all widgets, auto-switch to Question tab if blocked
- On answer submit: POST tool result, switch to Progress tab, resume polling
- On `d`: show confirmation dialog, then DELETE session

### Task 11: Integration and install verification
- `__main__.py` for `python -m autopilot_tui` entry
- Test pip install works: `pip install -e cli/`
- Smoke test: verify app launches and shows error when config missing
- Manual integration test checklist in PR description
