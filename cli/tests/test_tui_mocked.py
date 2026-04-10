"""Mock-based TUI tests — no API key required.

These tests exercise the TUI logic with fake data, covering the
question/answer flow and artifacts tab population.
"""

from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock, MagicMock

import pytest

from autopilot_tui.api import AutopilotAPI
from autopilot_tui.app import AutopilotApp


# ── Helpers ──────────────────────────────────────────────────────────────────


def _make_api(sessions: list[dict], events_by_id: dict[str, list[dict]] | None = None) -> AutopilotAPI:
    """Return a mock AutopilotAPI with canned responses."""
    api = MagicMock(spec=AutopilotAPI)
    api.list_sessions = AsyncMock(return_value=sessions)
    if events_by_id is not None:
        async def _get_events(session_id: str, **kwargs: object) -> list[dict]:
            return events_by_id.get(session_id, [])
        api.get_events = AsyncMock(side_effect=_get_events)
    else:
        api.get_events = AsyncMock(return_value=[])
    api.send_tool_result = AsyncMock(return_value={})
    return api


def _make_app(sessions: list[dict], events_by_id: dict[str, list[dict]] | None = None) -> AutopilotApp:
    api = _make_api(sessions, events_by_id)
    return AutopilotApp(api)


# ── Fixtures ─────────────────────────────────────────────────────────────────


BLOCKED_SESSIONS = [
    {
        "id": "sess-blocked",
        "title": "My blocked session",
        "status": "idle",
        "created_at": "2024-01-01T00:00:00Z",
    }
]

BLOCKED_EVENTS = [
    {
        "type": "agent.message",
        "content": [{"type": "text", "text": "## Phase 4: Implementation\nStarting work."}],
        "created_at": "2024-01-01T00:00:01Z",
    },
    {
        "type": "agent.custom_tool_use",
        "name": "ask_user",
        "id": "tool-ask-001",
        "input": {
            "question": "Which approach should I take?",
            "context": "Need guidance on direction.",
            "options": ["Option Alpha", "Option Beta", "Option Gamma"],
        },
        "created_at": "2024-01-01T00:00:02Z",
    },
    {
        "type": "session.status_idle",
        "stop_reason": {"type": "requires_action"},
        "created_at": "2024-01-01T00:00:03Z",
    },
]

ARTIFACT_SESSIONS = [
    {
        "id": "sess-artifacts",
        "title": "Session with writes",
        "status": "running",
        "created_at": "2024-01-01T00:00:00Z",
        "usage": {},
    }
]

ARTIFACT_EVENTS = [
    {
        "type": "agent.message",
        "content": [{"type": "text", "text": "## Phase 4: Implementation\nWriting files."}],
        "created_at": "2024-01-01T00:00:01Z",
    },
    {
        "type": "agent.tool_use",
        "name": "write",
        "id": "ev-write-1",
        "input": {"file_path": "/workspace/repo/src/main.py"},
        "processed_at": "2024-01-01T00:00:02Z",
    },
    {
        "type": "agent.tool_use",
        "name": "write",
        "id": "ev-write-2",
        "input": {"file_path": "/workspace/repo/tests/test_main.py"},
        "processed_at": "2024-01-01T00:00:03Z",
    },
    {
        "type": "agent.tool_use",
        "name": "write",
        "id": "ev-write-3",
        "input": {"file_path": "/workspace/repo/src/main.py"},  # duplicate — should be deduped
        "processed_at": "2024-01-01T00:00:04Z",
    },
    {
        "type": "session.status_running",
        "created_at": "2024-01-01T00:00:05Z",
    },
]


# ── Question / Answer flow tests ─────────────────────────────────────────────


@pytest.mark.asyncio
async def test_question_widget_renders_for_blocked_session():
    """QuestionWidget shows question text and options when session is blocked."""
    app = _make_app(BLOCKED_SESSIONS, {"sess-blocked": BLOCKED_EVENTS})

    async with app.run_test(size=(120, 40)) as pilot:
        await asyncio.sleep(2)
        await pilot.pause()

        # Select the blocked session
        from autopilot_tui.widgets.session_list import SessionSelected
        app.post_message(SessionSelected("sess-blocked"))
        await asyncio.sleep(2)
        await pilot.pause()

        # Tab should have auto-switched to the question tab
        from textual.widgets import TabbedContent
        tc = app.query_one("#tabs", TabbedContent)
        assert tc.active == "tab-question", (
            f"Expected tab-question (session is blocked), got {tc.active}"
        )

        # QuestionWidget body should show the question text and all options
        from autopilot_tui.widgets.question import QuestionWidget
        qw = app.query_one("#question-widget", QuestionWidget)
        content = str(qw._body_content.render())

        assert "Which approach should I take?" in content, (
            f"Question text missing. Got: {content[:300]}"
        )
        assert "Option Alpha" in content, f"Option Alpha missing. Got: {content[:300]}"
        assert "Option Beta" in content, f"Option Beta missing. Got: {content[:300]}"
        assert "Option Gamma" in content, f"Option Gamma missing. Got: {content[:300]}"
        # Option labels should display as literal [A], [B], [C]
        assert "[A]" in content, f"Option label [A] missing (markup escaping bug). Got: {content[:300]}"
        assert "[B]" in content, f"Option label [B] missing. Got: {content[:300]}"
        assert "[C]" in content, f"Option label [C] missing. Got: {content[:300]}"

        # tool_use_id should be stored
        assert qw._tool_use_id == "tool-ask-001", (
            f"tool_use_id not set. Got: {qw._tool_use_id!r}"
        )


@pytest.mark.asyncio
async def test_question_submit_sends_answer():
    """Typing an answer and pressing Enter calls send_tool_result."""
    api = _make_api(BLOCKED_SESSIONS, {"sess-blocked": BLOCKED_EVENTS})
    app = AutopilotApp(api)

    async with app.run_test(size=(120, 40)) as pilot:
        await asyncio.sleep(2)
        await pilot.pause()

        from autopilot_tui.widgets.session_list import SessionSelected
        app.post_message(SessionSelected("sess-blocked"))
        await asyncio.sleep(2)
        await pilot.pause()

        # Focus the answer input and type
        from textual.widgets import Input
        inp = app.query_one("#answer-input", Input)
        inp.focus()
        await pilot.pause()

        inp.value = "Option Alpha"
        await pilot.press("enter")
        await asyncio.sleep(1)
        await pilot.pause()

        assert api.send_tool_result.called, "send_tool_result was not called after submitting"
        call_args = api.send_tool_result.call_args
        assert call_args[0][1] == "tool-ask-001", (
            f"Wrong tool_use_id. Expected tool-ask-001, got {call_args[0][1]!r}"
        )
        assert call_args[0][2] == "Option Alpha", (
            f"Wrong answer text. Expected 'Option Alpha', got {call_args[0][2]!r}"
        )


@pytest.mark.asyncio
async def test_question_submit_via_button():
    """Clicking the Send button also calls send_tool_result."""
    api = _make_api(BLOCKED_SESSIONS, {"sess-blocked": BLOCKED_EVENTS})
    app = AutopilotApp(api)

    async with app.run_test(size=(120, 40)) as pilot:
        await asyncio.sleep(2)
        await pilot.pause()

        from autopilot_tui.widgets.session_list import SessionSelected
        app.post_message(SessionSelected("sess-blocked"))
        await asyncio.sleep(2)
        await pilot.pause()

        from textual.widgets import Input
        inp = app.query_one("#answer-input", Input)
        inp.focus()
        inp.value = "My button answer"
        await pilot.pause()

        # btn.press() is the reliable way to fire Button.Pressed in headless tests
        from textual.widgets import Button
        app.query_one("#submit-btn", Button).press()
        await asyncio.sleep(1)
        await pilot.pause()

        assert api.send_tool_result.called, "send_tool_result not called via button"
        assert api.send_tool_result.call_args[0][2] == "My button answer"


@pytest.mark.asyncio
async def test_answered_question_not_shown():
    """A question whose tool_use_id has a matching result is not shown."""
    answered_events = BLOCKED_EVENTS + [
        {
            "type": "user.custom_tool_result",
            "custom_tool_use_id": "tool-ask-001",
            "content": [{"type": "text", "text": "Option Alpha"}],
        }
    ]
    app = _make_app(BLOCKED_SESSIONS, {"sess-blocked": answered_events})

    async with app.run_test(size=(120, 40)) as pilot:
        await asyncio.sleep(2)
        await pilot.pause()

        from autopilot_tui.widgets.session_list import SessionSelected
        app.post_message(SessionSelected("sess-blocked"))
        await asyncio.sleep(2)
        await pilot.pause()

        from autopilot_tui.widgets.question import QuestionWidget
        qw = app.query_one("#question-widget", QuestionWidget)
        assert qw._tool_use_id == "", (
            f"Answered question should clear tool_use_id, got: {qw._tool_use_id!r}"
        )
        content = str(qw._body_content.render())
        assert "No pending question" in content, (
            f"Answered question should show 'No pending question'. Got: {content[:200]}"
        )


# ── Artifacts tab tests ───────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_artifacts_tab_shows_written_files():
    """ArtifactsWidget lists files from write tool_use events."""
    app = _make_app(ARTIFACT_SESSIONS, {"sess-artifacts": ARTIFACT_EVENTS})

    async with app.run_test(size=(120, 40)) as pilot:
        await asyncio.sleep(2)
        await pilot.pause()

        from autopilot_tui.widgets.session_list import SessionSelected
        app.post_message(SessionSelected("sess-artifacts"))
        await asyncio.sleep(2)
        await pilot.pause()

        from autopilot_tui.widgets.artifacts import ArtifactsWidget
        aw = app.query_one("#artifacts-widget", ArtifactsWidget)
        content = str(aw._content.render())

        assert "file" in content.lower(), (
            f"Artifacts tab should mention 'file'. Got: {content[:300]}"
        )
        # Deduplication: /workspace/repo/src/main.py appears twice but counts once
        assert "2 file" in content, (
            f"Expected 2 unique files (deduped). Got: {content[:300]}"
        )
        assert "src/main.py" in content, f"main.py not in artifacts. Got: {content[:300]}"
        assert "tests/test_main.py" in content, (
            f"test_main.py not in artifacts. Got: {content[:300]}"
        )


@pytest.mark.asyncio
async def test_artifacts_tab_empty_for_no_writes():
    """ArtifactsWidget shows placeholder when session has no write events."""
    no_write_events = [
        {
            "type": "agent.tool_use",
            "name": "bash",
            "id": "ev-bash-1",
            "input": {"command": "ls -la"},
        },
        {"type": "session.status_running"},
    ]
    sessions = [{"id": "sess-no-write", "title": "No writes", "status": "running", "created_at": "2024-01-01T00:00:00Z"}]
    app = _make_app(sessions, {"sess-no-write": no_write_events})

    async with app.run_test(size=(120, 40)) as pilot:
        await asyncio.sleep(2)
        await pilot.pause()

        from autopilot_tui.widgets.session_list import SessionSelected
        app.post_message(SessionSelected("sess-no-write"))
        await asyncio.sleep(2)
        await pilot.pause()

        # Switch to artifacts tab
        await pilot.press("2")
        await pilot.pause()

        from autopilot_tui.widgets.artifacts import ArtifactsWidget
        aw = app.query_one("#artifacts-widget", ArtifactsWidget)
        content = str(aw._content.render())
        assert "No artifacts" in content, (
            f"Expected 'No artifacts' placeholder. Got: {content[:200]}"
        )
