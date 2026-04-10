"""Autopilot TUI — main application."""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

from textual import on, work
from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Container, Horizontal, Vertical
from textual.css.query import NoMatches
from textual.widgets import Footer, Label, Static, TabbedContent, TabPane

from autopilot_tui.api import AutopilotAPI
from autopilot_tui.parser import (
    extract_artifacts,
    extract_phases,
    extract_question,
    is_blocked,
    session_status,
    time_ago,
)
from autopilot_tui.theme import AUTOPILOT_THEME, THEME_CSS
from autopilot_tui.widgets.artifacts import ArtifactsWidget
from autopilot_tui.widgets.events import EventStreamWidget
from autopilot_tui.widgets.progress import ProgressWidget
from autopilot_tui.widgets.question import AnswerSubmitted, QuestionWidget
from autopilot_tui.widgets.session_list import SessionListWidget, SessionSelected


def _load_config() -> tuple[str, str]:
    api_key = os.environ.get("ANTHROPIC_API_KEY", "").strip()
    if not api_key:
        print("ERROR: ANTHROPIC_API_KEY is not set.", file=sys.stderr)
        sys.exit(1)

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
    sys.exit(1)


class AutopilotApp(App[None]):
    CSS = THEME_CSS

    BINDINGS = [
        Binding("q", "quit", "Quit"),
        Binding("r", "refresh", "Refresh"),
        Binding("1", "tab('tab-progress')", "Progress"),
        Binding("2", "tab('tab-artifacts')", "Artifacts"),
        Binding("3", "tab('tab-question')", "Question"),
    ]

    def __init__(self, api: AutopilotAPI) -> None:
        super().__init__()
        self.register_theme(AUTOPILOT_THEME)
        self.theme = "autopilot"
        self._api = api
        self._selected_id: str | None = None
        self._sessions: list[dict] = []
        self._events: dict[str, list[dict]] = {}

    def compose(self) -> ComposeResult:
        with Horizontal():
            with Vertical(id="left-panel"):
                yield SessionListWidget(id="session-list-widget")
            with Vertical(id="right-panels"):
                with TabbedContent(id="tabs"):
                    with TabPane("Progress", id="tab-progress"):
                        yield ProgressWidget(id="progress-widget")
                    with TabPane("Artifacts", id="tab-artifacts"):
                        yield ArtifactsWidget(id="artifacts-widget")
                    with TabPane("Question", id="tab-question"):
                        yield QuestionWidget(id="question-widget")
                with Container(id="right-bottom"):
                    yield EventStreamWidget(id="events-widget")
        yield Footer()

    def on_mount(self) -> None:
        self.query_one("#left-panel").styles.width = "34%"
        self.query_one("#right-panels").styles.width = "66%"
        self.query_one("#right-bottom").styles.height = 18
        self._do_load_sessions()
        self.set_interval(30, self._do_load_sessions)
        self.set_interval(5, self._do_poll)

    # ── Data ────────────────────────────────────────────────────────────────

    @work(exclusive=True, group="load")
    async def _do_load_sessions(self) -> None:
        try:
            sessions = await self._api.list_sessions()
            # Preserve existing _display_status from events cache
            for s in sessions:
                sid = s.get("id", "")
                if sid in self._events:
                    s["_display_status"] = session_status(s, self._events[sid])
                else:
                    s["_display_status"] = _raw_status(s)
            self._sessions = sessions
            self._update_session_list()
        except Exception as e:
            self.log.error(f"load_sessions: {e}")

    @work(exclusive=True, group="events")
    async def _do_load_events(self, session_id: str) -> None:
        try:
            events = await self._api.get_events(session_id)
            self._events[session_id] = events
            # Update the status on the session dict
            session = self._find_session(session_id)
            if session:
                session["_display_status"] = session_status(session, events)
                self._update_session_list()
            # Update detail panels
            self._update_detail_panels(session_id)
        except Exception as e:
            self.log.error(f"load_events: {e}")

    @work(exclusive=True, group="poll")
    async def _do_poll(self) -> None:
        if not self._selected_id:
            return
        session = self._find_session(self._selected_id)
        if not session:
            return
        status = session.get("_display_status", "done")
        if status not in ("running", "blocked"):
            return
        try:
            events = await self._api.get_events(self._selected_id)
            self._events[self._selected_id] = events
            session["_display_status"] = session_status(session, events)
            self._update_detail_panels(self._selected_id)
        except Exception as e:
            self.log.error(f"poll: {e}")

    def _find_session(self, sid: str) -> dict | None:
        for s in self._sessions:
            if s.get("id") == sid:
                return s
        return None

    # ── UI updates (always called from worker context) ──────────────────────

    def _update_session_list(self) -> None:
        """Push current sessions to the list widget."""
        try:
            self.query_one("#session-list-widget", SessionListWidget).update_sessions(
                self._sessions
            )
        except NoMatches:
            pass

    def _update_detail_panels(self, session_id: str) -> None:
        """Update all right-side panels for the given session."""
        if session_id != self._selected_id:
            return
        session = self._find_session(session_id) or {}
        events = self._events.get(session_id, [])

        # Event stream
        try:
            self.query_one("#events-widget", EventStreamWidget).update_events(events)
        except NoMatches:
            pass

        # Progress tab
        try:
            self.query_one("#progress-widget", ProgressWidget).update_data(
                session, events
            )
        except NoMatches:
            pass

        # Artifacts tab
        try:
            self.query_one("#artifacts-widget", ArtifactsWidget).update_data(
                extract_artifacts(events)
            )
        except NoMatches:
            pass

        # Question tab
        question = extract_question(events)
        try:
            self.query_one("#question-widget", QuestionWidget).load_question(question)
        except NoMatches:
            pass

        # Auto-switch to question tab if blocked
        if question and session.get("_display_status") == "blocked":
            try:
                self.query_one("#tabs", TabbedContent).active = "tab-question"
            except NoMatches:
                pass

    # ── Events ──────────────────────────────────────────────────────────────

    @on(SessionSelected)
    def _on_session_selected(self, message: SessionSelected) -> None:
        self._selected_id = message.session_id
        self._do_load_events(message.session_id)

    @on(AnswerSubmitted)
    def _on_answer_submitted(self, message: AnswerSubmitted) -> None:
        self._do_send_answer(message.tool_use_id, message.answer)

    @work(exclusive=True, group="answer")
    async def _do_send_answer(self, tool_use_id: str, answer: str) -> None:
        if not self._selected_id:
            return
        try:
            await self._api.send_tool_result(self._selected_id, tool_use_id, answer)
            self.notify("Answer sent", severity="information")
            events = await self._api.get_events(self._selected_id)
            self._events[self._selected_id] = events
            self._update_detail_panels(self._selected_id)
        except Exception as e:
            self.notify(f"Failed: {e}", severity="error")

    # ── Actions ─────────────────────────────────────────────────────────────

    def action_refresh(self) -> None:
        self._do_load_sessions()
        if self._selected_id:
            self._do_load_events(self._selected_id)

    def action_tab(self, tab_id: str) -> None:
        try:
            self.query_one("#tabs", TabbedContent).active = tab_id
        except NoMatches:
            pass


def _raw_status(session: dict) -> str:
    raw = (session.get("status") or "").lower()
    if raw in ("running", "active", "rescheduling"):
        return "running"
    if raw == "idle":
        return "blocked"
    if raw == "terminated":
        return "done"
    return "done"


def main() -> None:
    api_key, environment_id = _load_config()
    api = AutopilotAPI(api_key, environment_id)
    app = AutopilotApp(api)
    app.run()
