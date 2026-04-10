"""Autopilot TUI — main application."""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path
from typing import Any

from textual import on, work
from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Container, Horizontal, Vertical
from textual.css.query import NoMatches
from textual.screen import ModalScreen
from textual.widget import Widget
from textual.widgets import Button, Footer, Label, Static, TabbedContent, TabPane

from autopilot_tui.api import AutopilotAPI
from autopilot_tui.parser import (
    extract_artifacts,
    extract_phases,
    extract_question,
    is_blocked,
    session_status,
    time_ago,
)
from autopilot_tui.theme import THEME_CSS
from autopilot_tui.widgets.artifacts import ArtifactsWidget
from autopilot_tui.widgets.events import EventStreamWidget
from autopilot_tui.widgets.progress import ProgressWidget
from autopilot_tui.widgets.question import AnswerSubmitted, QuestionWidget
from autopilot_tui.widgets.session_list import SessionListWidget, SessionSelected


# ── Config loading ─────────────────────────────────────────────────────────────

def _load_config() -> tuple[str, str]:
    """Return (api_key, environment_id) or raise SystemExit with message."""
    api_key = os.environ.get("ANTHROPIC_API_KEY", "").strip()
    if not api_key:
        print("ERROR: ANTHROPIC_API_KEY is not set.", file=sys.stderr)
        print("Export it or add it to your .env file.", file=sys.stderr)
        sys.exit(1)

    # Search for environment_id in known config locations
    candidates = [
        Path.home() / ".autopilot" / "config.json",
        Path.cwd() / ".superpowers" / "autopilot-config.json",
    ]
    for path in candidates:
        if path.exists():
            try:
                data = json.loads(path.read_text())
                env_id = data.get("environment_id", "")
                if env_id:
                    return api_key, env_id
            except Exception:
                pass

    print("ERROR: No autopilot config found.", file=sys.stderr)
    print(
        "Expected environment_id in ~/.autopilot/config.json or "
        ".superpowers/autopilot-config.json",
        file=sys.stderr,
    )
    sys.exit(1)


# ── Confirmation dialog ────────────────────────────────────────────────────────

class ConfirmDialog(ModalScreen[bool]):
    DEFAULT_CSS = """
    ConfirmDialog {
        align: center middle;
    }
    #dialog {
        background: $surface;
        border: solid $border;
        padding: 2 4;
        width: 60;
        height: auto;
    }
    #dialog-buttons {
        layout: horizontal;
        height: auto;
        margin-top: 2;
        align: right middle;
    }
    """

    def __init__(self, title: str, message: str) -> None:
        super().__init__()
        self._title = title
        self._message = message

    def compose(self) -> ComposeResult:
        with Container(id="dialog"):
            yield Label(self._title, id="dialog-title")
            yield Label(self._message, id="dialog-message")
            with Container(id="dialog-buttons"):
                yield Button("Cancel", id="cancel-btn")
                yield Button("Confirm", id="confirm-btn", variant="error")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        self.dismiss(event.button.id == "confirm-btn")


# ── Main application ───────────────────────────────────────────────────────────

class AutopilotApp(App[None]):
    CSS = THEME_CSS
    BINDINGS = [
        Binding("q", "quit", "Quit"),
        Binding("r", "refresh", "Refresh"),
        Binding("d", "terminate", "Terminate session"),
        Binding("1", "tab_progress", "Progress"),
        Binding("2", "tab_artifacts", "Artifacts"),
        Binding("3", "tab_question", "Question"),
        Binding("a", "quick_answer('a')", "Option A", show=False),
        Binding("b", "quick_answer('b')", "Option B", show=False),
        Binding("c", "quick_answer('c')", "Option C", show=False),
    ]

    def __init__(self, api: AutopilotAPI) -> None:
        super().__init__()
        self._api = api
        self._selected_id: str | None = None
        self._sessions: list[dict] = []
        # Per-session event cache: session_id → list[event]
        self._events: dict[str, list[dict]] = {}
        # Last event ID seen per session for incremental fetching
        self._last_event_id: dict[str, str] = {}

    def compose(self) -> ComposeResult:
        with Horizontal():
            # Left panel — session list
            with Vertical(id="left-panel"):
                yield SessionListWidget(id="session-list-widget")

            # Right panels
            with Vertical(id="right-panels"):
                # Right-top — tabbed detail view
                with TabbedContent(id="right-top-tabs"):
                    with TabPane("Progress", id="tab-progress"):
                        yield ProgressWidget(id="progress-widget")
                    with TabPane("Artifacts", id="tab-artifacts"):
                        yield ArtifactsWidget(id="artifacts-widget")
                    with TabPane("Question", id="tab-question"):
                        yield QuestionWidget(id="question-widget")

                # Right-bottom — event stream
                with Container(id="right-bottom"):
                    yield EventStreamWidget(id="events-widget")

        yield Footer()

    def on_mount(self) -> None:
        self.dark = False  # Force light mode
        # Set panel sizes via inline styles
        self.query_one("#left-panel").styles.width = "34%"
        self.query_one("#right-panels").styles.width = "66%"
        self.query_one("#right-bottom").styles.height = 18

        # Initial data load
        self._load_sessions()
        # Periodic timers
        self.set_interval(30, self._refresh_sessions_background)
        self.set_interval(5, self._poll_active_session)

    # ── Data loading ─────────────────────────────────────────────────────────

    @work(exclusive=True, group="sessions")
    async def _load_sessions(self) -> None:
        try:
            sessions = await self._api.list_sessions()
            self._sessions = sessions
            # Annotate display status (no events loaded yet for unselected)
            for s in self._sessions:
                s.setdefault("_display_status", _raw_status(s))
            slw: SessionListWidget = self.query_one("#session-list-widget", SessionListWidget)
            slw.update_sessions(self._sessions)
        except Exception as e:
            self.notify(f"Failed to load sessions: {e}", severity="error")

    @work(exclusive=True, group="sessions")
    async def _refresh_sessions_background(self) -> None:
        """30s background refresh of session list (status only)."""
        try:
            sessions = await self._api.list_sessions()
            self._sessions = sessions
            for s in self._sessions:
                sid = s.get("id", "")
                if sid in self._events:
                    s["_display_status"] = session_status(s, self._events[sid])
                    phases = extract_phases(self._events[sid])
                    s["_current_phase"] = phases[-1]["name"] if phases else ""
                else:
                    s.setdefault("_display_status", _raw_status(s))
            slw: SessionListWidget = self.query_one("#session-list-widget", SessionListWidget)
            slw.update_sessions(self._sessions)
        except Exception:
            pass  # Silent background refresh

    @work(exclusive=True, group="events")
    async def _load_session_events(self, session_id: str) -> None:
        try:
            after = self._last_event_id.get(session_id)
            events = await self._api.get_events(session_id, after_event_id=after)
            if after and events:
                self._events[session_id] = self._events.get(session_id, []) + events
            elif events:
                self._events[session_id] = events
            elif session_id not in self._events:
                self._events[session_id] = []

            if events:
                last_id = events[-1].get("id")
                if last_id:
                    self._last_event_id[session_id] = last_id

            self._update_ui_for_session(session_id)
        except Exception as e:
            self.notify(f"Error loading events: {e}", severity="error")

    @work(exclusive=True, group="poll")
    async def _poll_active_session(self) -> None:
        if not self._selected_id:
            return
        session = self._get_session(self._selected_id)
        if session is None:
            return
        status = session.get("_display_status", _raw_status(session))
        if status not in ("running", "blocked"):
            return
        self._load_session_events(self._selected_id)

    def _get_session(self, session_id: str) -> dict | None:
        for s in self._sessions:
            if s.get("id") == session_id:
                return s
        return None

    # ── UI update ─────────────────────────────────────────────────────────────

    def _update_ui_for_session(self, session_id: str) -> None:
        if session_id != self._selected_id:
            return
        session = self._get_session(session_id) or {}
        events = self._events.get(session_id, [])

        # Annotate session with derived status and current phase
        status = session_status(session, events)
        session["_display_status"] = status
        phases = extract_phases(events)
        session["_current_phase"] = phases[-1]["name"] if phases else ""

        # Update session list (re-sort with new status)
        for s in self._sessions:
            if s.get("id") == session_id:
                s["_display_status"] = status
                s["_current_phase"] = session.get("_current_phase", "")
        try:
            slw: SessionListWidget = self.query_one("#session-list-widget", SessionListWidget)
            slw.update_sessions(self._sessions)
        except NoMatches:
            pass

        # Update event stream
        try:
            ew: EventStreamWidget = self.query_one("#events-widget", EventStreamWidget)
            ew.update_events(events)
        except NoMatches:
            pass

        # Update progress tab
        try:
            pw: ProgressWidget = self.query_one("#progress-widget", ProgressWidget)
            pw.update(session, events)
        except NoMatches:
            pass

        # Update artifacts tab
        try:
            aw: ArtifactsWidget = self.query_one("#artifacts-widget", ArtifactsWidget)
            aw.update(extract_artifacts(events))
        except NoMatches:
            pass

        # Update question tab and auto-switch
        question = extract_question(events)
        try:
            qw: QuestionWidget = self.query_one("#question-widget", QuestionWidget)
            qw.load_question(question)
        except NoMatches:
            pass

        if question and status == "blocked":
            self._switch_tab("tab-question")

    def _switch_tab(self, tab_id: str) -> None:
        try:
            tc: TabbedContent = self.query_one("#right-top-tabs", TabbedContent)
            tc.active = tab_id
        except NoMatches:
            pass

    # ── Message handlers ──────────────────────────────────────────────────────

    @on(SessionSelected)
    def on_session_selected(self, message: SessionSelected) -> None:
        self._selected_id = message.session_id
        self._load_session_events(message.session_id)

    @on(AnswerSubmitted)
    def on_answer_submitted(self, message: AnswerSubmitted) -> None:
        self._send_answer(message.tool_use_id, message.answer)

    @work(exclusive=True, group="answer")
    async def _send_answer(self, tool_use_id: str, answer: str) -> None:
        if not self._selected_id:
            return
        try:
            await self._api.send_tool_result(self._selected_id, tool_use_id, answer)
            self.notify("Answer sent ✓", severity="information")
            self._switch_tab("tab-progress")
            # Clear last event ID so we pick up the new events
            self._last_event_id.pop(self._selected_id, None)
            # Load fresh events
            self._load_session_events(self._selected_id)
        except Exception as e:
            self.notify(f"Failed to send answer: {e}", severity="error")

    # ── Actions ───────────────────────────────────────────────────────────────

    def action_refresh(self) -> None:
        self._load_sessions()
        if self._selected_id:
            self._last_event_id.pop(self._selected_id, None)
            self._load_session_events(self._selected_id)

    def action_tab_progress(self) -> None:
        self._switch_tab("tab-progress")

    def action_tab_artifacts(self) -> None:
        self._switch_tab("tab-artifacts")

    def action_tab_question(self) -> None:
        self._switch_tab("tab-question")

    def action_quick_answer(self, letter: str) -> None:
        try:
            tc: TabbedContent = self.query_one("#right-top-tabs", TabbedContent)
            if tc.active != "tab-question":
                return
            qw: QuestionWidget = self.query_one("#question-widget", QuestionWidget)
            qw.select_option(letter)
        except NoMatches:
            pass

    def action_terminate(self) -> None:
        if not self._selected_id:
            self.notify("No session selected", severity="warning")
            return
        session = self._get_session(self._selected_id)
        name = (session or {}).get("title") or self._selected_id[:12]
        self._confirm_terminate(name)

    @work
    async def _confirm_terminate(self, name: str) -> None:
        confirmed = await self.push_screen_wait(
            ConfirmDialog(
                title="Terminate session?",
                message=f"This will stop session: {name}\nThis cannot be undone.",
            )
        )
        if confirmed and self._selected_id:
            try:
                await self._api.delete_session(self._selected_id)
                self.notify(f"Session {name} terminated", severity="warning")
                self._selected_id = None
                self._load_sessions()
            except Exception as e:
                self.notify(f"Failed to terminate: {e}", severity="error")


# ── Status helper ──────────────────────────────────────────────────────────────

def _raw_status(session: dict) -> str:
    raw = (session.get("status") or "").lower()
    if raw in ("complete", "completed", "done"):
        return "done"
    if raw in ("error", "failed"):
        return "error"
    if raw in ("running", "active"):
        return "running"
    return "done"


# ── Entry point ────────────────────────────────────────────────────────────────

def main() -> None:
    api_key, environment_id = _load_config()
    api = AutopilotAPI(api_key, environment_id)
    app = AutopilotApp(api)
    app.run()
    # httpx client is garbage-collected; no manual cleanup needed
