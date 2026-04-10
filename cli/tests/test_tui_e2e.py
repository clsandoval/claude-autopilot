"""End-to-end tests for Autopilot TUI using Textual's Pilot."""

import asyncio
import json
import os
import sys

import pytest

# Skip entire module if no API key
pytestmark = pytest.mark.skipif(
    not os.environ.get("ANTHROPIC_API_KEY"),
    reason="ANTHROPIC_API_KEY not set",
)


@pytest.fixture
def api_key():
    return os.environ["ANTHROPIC_API_KEY"]


@pytest.fixture
def environment_id():
    search = [
        os.path.expanduser("~/.autopilot/config.json"),
        os.path.join(os.getcwd(), ".superpowers/autopilot-config.json"),
        os.path.expanduser("~/cs/monorepo/.superpowers/autopilot-config.json"),
    ]
    for path in search:
        if os.path.exists(path):
            data = json.loads(open(path).read())
            eid = data.get("environment_id", "")
            if eid:
                return eid
    pytest.skip("No autopilot config found")


@pytest.fixture
def app(api_key, environment_id):
    from autopilot_tui.api import AutopilotAPI
    from autopilot_tui.app import AutopilotApp

    api = AutopilotAPI(api_key, environment_id)
    return AutopilotApp(api)


# ── Test 1: App launches without errors ──────────────────────────────────────


@pytest.mark.asyncio
async def test_app_launches(app):
    """App mounts, sets theme, renders footer."""
    async with app.run_test(size=(120, 40)) as pilot:
        await asyncio.sleep(2)
        await pilot.pause()

        # Theme applied
        assert app.theme == "autopilot"

        # Footer exists
        from textual.widgets import Footer
        footer = app.query_one(Footer)
        assert footer is not None


# ── Test 2: Sessions load into the list ──────────────────────────────────────


@pytest.mark.asyncio
async def test_sessions_load(app):
    """Sessions appear in the ListView after mount."""
    async with app.run_test(size=(120, 40)) as pilot:
        await asyncio.sleep(3)
        await pilot.pause()

        assert len(app._sessions) > 0, "No sessions loaded from API"

        from textual.widgets import ListView
        lv = app.query_one("#session-listview", ListView)
        assert len(lv.children) > 0, "ListView has no children"
        assert len(lv.children) == len(app._sessions), (
            f"ListView has {len(lv.children)} items but {len(app._sessions)} sessions"
        )


# ── Test 3: Selecting a session loads events ─────────────────────────────────


@pytest.mark.asyncio
async def test_select_session_loads_events(app):
    """Selecting a session populates events."""
    async with app.run_test(size=(120, 40)) as pilot:
        await asyncio.sleep(3)
        await pilot.pause()

        assert len(app._sessions) > 0, "No sessions to select"

        # Pick the first session from the sorted list
        first_sid = app._sessions[0].get("id")

        # Post the selection message directly (like the widget would)
        from autopilot_tui.widgets.session_list import SessionSelected
        app.post_message(SessionSelected(first_sid))

        await asyncio.sleep(4)
        await pilot.pause()

        assert app._selected_id == first_sid, f"Selected ID not set"
        assert first_sid in app._events, f"Events not loaded for {first_sid}"
        events = app._events[first_sid]
        assert len(events) > 0, "No events returned for session"


# ── Test 4: Event stream widget shows filtered events ────────────────────────


@pytest.mark.asyncio
async def test_event_stream_shows_events(app):
    """Event stream widget renders lines after session selection."""
    async with app.run_test(size=(120, 40)) as pilot:
        await asyncio.sleep(3)
        await pilot.pause()

        if not app._sessions:
            pytest.skip("No sessions available")

        first_sid = app._sessions[0].get("id")
        from autopilot_tui.widgets.session_list import SessionSelected
        app.post_message(SessionSelected(first_sid))

        await asyncio.sleep(4)
        await pilot.pause()

        # Verify events were loaded
        assert first_sid in app._events, "Events not loaded"
        assert len(app._events[first_sid]) > 0, "No events"

        # RichLog should have content
        from textual.widgets import RichLog
        log = app.query_one("#events-rich-log", RichLog)
        assert len(log.lines) > 0, "Event stream RichLog is empty"


# ── Test 5: Progress widget shows phases ─────────────────────────────────────


@pytest.mark.asyncio
async def test_progress_widget_shows_phases(app):
    """Progress widget renders phase and usage info."""
    async with app.run_test(size=(120, 40)) as pilot:
        await asyncio.sleep(3)
        await pilot.pause()

        if not app._sessions:
            pytest.skip("No sessions available")

        first_sid = app._sessions[0].get("id")
        from autopilot_tui.widgets.session_list import SessionSelected
        app.post_message(SessionSelected(first_sid))

        await asyncio.sleep(4)
        await pilot.pause()

        from autopilot_tui.widgets.progress import ProgressWidget
        pw = app.query_one("#progress-widget", ProgressWidget)
        # Static.update() sets the content — check via render or _content._renderable
        content = str(pw._content.render())
        assert "Phase" in content or "phase" in content or "Phases" in content, (
            f"Progress widget missing phase info. Got: {content[:300]}"
        )


# ── Test 6: Tab switching works ──────────────────────────────────────────────


@pytest.mark.asyncio
async def test_tab_switching(app):
    """Pressing 1/2/3 switches tabs."""
    async with app.run_test(size=(120, 40)) as pilot:
        await asyncio.sleep(2)
        await pilot.pause()

        from textual.widgets import TabbedContent
        tc = app.query_one("#tabs", TabbedContent)

        await pilot.press("2")
        await pilot.pause()
        assert tc.active == "tab-artifacts", f"Tab should be artifacts, got {tc.active}"

        await pilot.press("3")
        await pilot.pause()
        assert tc.active == "tab-question", f"Tab should be question, got {tc.active}"

        await pilot.press("1")
        await pilot.pause()
        assert tc.active == "tab-progress", f"Tab should be progress, got {tc.active}"


# ── Test 7: Refresh keybinding works ─────────────────────────────────────────


@pytest.mark.asyncio
async def test_refresh_keybinding(app):
    """Pressing 'r' triggers a refresh without crashing."""
    async with app.run_test(size=(120, 40)) as pilot:
        await asyncio.sleep(2)
        await pilot.pause()

        initial_sessions = list(app._sessions)

        await pilot.press("r")
        await asyncio.sleep(2)
        await pilot.pause()

        # Should still have sessions (refresh reloads, doesn't clear)
        assert len(app._sessions) >= len(initial_sessions), "Sessions disappeared after refresh"


# ── Test 8: Session list doesn't rebuild on no-change refresh ────────────────


@pytest.mark.asyncio
async def test_session_list_no_unnecessary_rebuild(app):
    """Session list skips rebuild when nothing changed."""
    async with app.run_test(size=(120, 40)) as pilot:
        await asyncio.sleep(3)
        await pilot.pause()

        from autopilot_tui.widgets.session_list import SessionListWidget
        slw = app.query_one("#session-list-widget", SessionListWidget)

        # Call update with the same data — should be a no-op
        sessions_copy = [dict(s) for s in app._sessions]
        from textual.widgets import ListView
        lv = app.query_one("#session-listview", ListView)
        items_before = len(lv.children)

        slw.update_sessions(sessions_copy)
        await pilot.pause()

        items_after = len(lv.children)
        assert items_before == items_after


# ── Test 9: Artifacts tab shows files for sessions with writes ────────────────


@pytest.mark.asyncio
async def test_artifacts_tab_shows_files(app):
    """Artifacts tab shows written files for sessions that have them."""
    async with app.run_test(size=(120, 40)) as pilot:
        await asyncio.sleep(3)
        await pilot.pause()

        if not app._sessions:
            pytest.skip("No sessions available")

        # Find a session with artifacts (the TUI session has 14)
        from autopilot_tui.parser import extract_artifacts
        target_sid = None
        for s in app._sessions:
            sid = s.get("id")
            from autopilot_tui.widgets.session_list import SessionSelected
            app.post_message(SessionSelected(sid))
            await asyncio.sleep(3)
            await pilot.pause()
            events = app._events.get(sid, [])
            if extract_artifacts(events):
                target_sid = sid
                break

        if not target_sid:
            pytest.skip("No sessions with artifacts")

        from autopilot_tui.widgets.artifacts import ArtifactsWidget
        aw = app.query_one("#artifacts-widget", ArtifactsWidget)
        content = str(aw._content.render())
        assert "file" in content.lower(), f"Artifacts tab should show files. Got: {content[:200]}"


# ── Test 10: Screenshot captures without error ───────────────────────────────


@pytest.mark.asyncio
async def test_screenshot_renders(app):
    """App can export a screenshot SVG without crashing."""
    async with app.run_test(size=(120, 40)) as pilot:
        await asyncio.sleep(3)
        await pilot.pause()

        svg = app.export_screenshot()
        assert len(svg) > 100, "Screenshot SVG is too short"
        assert "<svg" in svg, "Screenshot doesn't contain SVG tag"
        # Our theme colors should appear
        assert "#FAF7F2" in svg.upper() or "#faf7f2" in svg, "Background color not in screenshot"
