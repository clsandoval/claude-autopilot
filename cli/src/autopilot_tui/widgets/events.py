"""Right-bottom event stream widget."""

from __future__ import annotations

from textual.app import ComposeResult
from textual.scroll_view import ScrollView
from textual.widget import Widget
from textual.widgets import Label, RichLog

from autopilot_tui.parser import format_event_line

_CLASS_TO_STYLE = {
    "event-phase":    "bold green",
    "event-question": "bold yellow",
    "event-line":     "dim",
}


class EventStreamWidget(Widget):
    DEFAULT_CSS = """
    EventStreamWidget {
        height: 100%;
        width: 100%;
    }
    #events-rich-log {
        height: 1fr;
        background: $surface;
        padding: 0 1;
    }
    """

    def compose(self) -> ComposeResult:
        yield Label("Event Stream", classes="panel-title")
        yield RichLog(id="events-rich-log", highlight=False, markup=True, wrap=False)

    def update_events(self, events: list[dict]) -> None:
        log: RichLog = self.query_one("#events-rich-log", RichLog)
        log.clear()
        for event in events:
            css_class, text = format_event_line(event)
            style = _CLASS_TO_STYLE.get(css_class, "")
            if style:
                log.write(f"[{style}]{text}[/{style}]")
            else:
                log.write(text)
