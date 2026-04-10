"""Left-panel session list widget."""

from __future__ import annotations

from textual.app import ComposeResult
from textual.message import Message
from textual.reactive import reactive
from textual.widget import Widget
from textual.widgets import Label, ListItem, ListView

from autopilot_tui.parser import time_ago

_STATUS_ICON = {
    "running": ("●", "status-running"),
    "blocked": ("◆", "status-blocked"),
    "done":    ("✓", "status-done"),
    "error":   ("✕", "status-error"),
}

_STATUS_ORDER = {"blocked": 0, "running": 1, "done": 2, "error": 3}


def _sort_key(s: dict) -> tuple:
    status = s.get("_display_status", "done")
    order = _STATUS_ORDER.get(status, 4)
    ts = s.get("created_at") or s.get("started_at") or ""
    return (order, ts)


class SessionSelected(Message):
    def __init__(self, session_id: str) -> None:
        super().__init__()
        self.session_id = session_id


class SessionListWidget(Widget):
    """Sorted, selectable session list."""

    selected_id: reactive[str | None] = reactive(None)

    DEFAULT_CSS = """
    SessionListWidget {
        width: 100%;
        height: 1fr;
    }
    #session-listview {
        height: 1fr;
    }
    """

    def __init__(self, **kwargs: object) -> None:
        super().__init__(**kwargs)
        self._sessions: list[dict] = []

    def compose(self) -> ComposeResult:
        yield Label("Sessions", classes="panel-title")
        yield ListView(id="session-listview")

    def update_sessions(self, sessions: list[dict]) -> None:
        sorted_sessions = sorted(sessions, key=_sort_key)
        # Only rebuild if session IDs or statuses changed
        new_keys = [(s.get("id"), s.get("_display_status")) for s in sorted_sessions]
        old_keys = [(s.get("id"), s.get("_display_status")) for s in self._sessions]
        if new_keys == old_keys:
            return
        self._sessions = sorted_sessions
        self._rebuild()

    def _rebuild(self) -> None:
        lv: ListView = self.query_one("#session-listview", ListView)
        saved_index = lv.index
        lv.clear()
        for session in self._sessions:
            item = self._make_item(session)
            lv.append(item)
        # Restore position
        if self.selected_id:
            self._apply_selection(self.selected_id)
        elif saved_index is not None and saved_index < len(self._sessions):
            lv.index = saved_index

    def _make_item(self, session: dict) -> ListItem:
        sid = session.get("id", "")
        title = session.get("title") or session.get("name") or sid[:12]
        status = session.get("_display_status", "done")
        icon, css_class = _STATUS_ICON.get(status, ("?", "status-done"))
        ts = time_ago(session.get("created_at") or session.get("started_at"))
        phase = session.get("_current_phase", "")

        status_label = Label(f"{icon} {status}", classes=f"session-meta {css_class}")
        name_label = Label(title[:36], classes="session-name")
        meta_label = Label(
            f"{ts}  {phase}"[:40] if phase else ts,
            classes="session-meta",
        )

        item = ListItem(name_label, status_label, meta_label, id=f"session-{sid}")
        return item

    def _apply_selection(self, session_id: str) -> None:
        lv: ListView = self.query_one("#session-listview", ListView)
        for i, session in enumerate(self._sessions):
            if session.get("id") == session_id:
                lv.index = i
                return

    def on_list_view_selected(self, event: ListView.Selected) -> None:
        item_id = event.item.id or ""
        if item_id.startswith("session-"):
            sid = item_id[len("session-"):]
            self.selected_id = sid
            self.post_message(SessionSelected(sid))
        event.stop()

    def on_list_view_highlighted(self, event: ListView.Highlighted) -> None:
        """Update selected_id on keyboard highlight."""
        if event.item is None:
            return
        item_id = event.item.id or ""
        if item_id.startswith("session-"):
            sid = item_id[len("session-"):]
            self.selected_id = sid
            self.post_message(SessionSelected(sid))
        event.stop()
