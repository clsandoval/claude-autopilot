"""Right-top Progress tab widget."""

from __future__ import annotations

from textual.app import ComposeResult
from textual.widget import Widget
from textual.widgets import Label, Static

from autopilot_tui.parser import (
    Decision,
    Phase,
    extract_decisions,
    extract_phases,
    time_ago,
)

_PHASE_ICON = {
    "complete": "✓",
    "active":   "◉",
    "pending":  "○",
}
_PHASE_CLASS = {
    "complete": "phase-complete",
    "active":   "phase-active",
    "pending":  "phase-pending",
}


class ProgressWidget(Widget):
    DEFAULT_CSS = """
    ProgressWidget {
        height: 100%;
        width: 100%;
        overflow-y: auto;
        padding: 1 2;
    }
    """

    def __init__(self, **kwargs: object) -> None:
        super().__init__(**kwargs)
        self._content = Static("")

    def compose(self) -> ComposeResult:
        yield self._content

    def update(self, session: dict, events: list[dict]) -> None:
        phases = extract_phases(events)
        decisions = extract_decisions(events)

        lines: list[str] = []

        # ── Phases ──────────────────────────────────────────────
        lines.append("[bold]Phases[/bold]")
        lines.append("─" * 40)
        if phases:
            for phase in phases:
                icon = _PHASE_ICON.get(phase["status"], "○")
                css = _PHASE_CLASS.get(phase["status"], "")
                ts = time_ago(phase.get("started_at"))
                suffix = f"  [{ts}]" if ts else ""
                color = {
                    "complete": "green",
                    "active": "yellow",
                    "pending": "dim",
                }.get(phase["status"], "")
                if color:
                    lines.append(f"[{color}]{icon} {phase['name']}{suffix}[/{color}]")
                else:
                    lines.append(f"{icon} {phase['name']}{suffix}")
        else:
            lines.append("[dim]No phases detected yet[/dim]")

        lines.append("")

        # ── Decisions ────────────────────────────────────────────
        lines.append("[bold]Decisions[/bold]")
        lines.append("─" * 40)
        if decisions:
            for d in decisions[-10:]:  # show last 10
                ts = time_ago(d.get("timestamp"))
                ts_str = f" [{ts}]" if ts else ""
                lines.append(f"  • {d['text'][:80]}[dim]{ts_str}[/dim]")
        else:
            lines.append("[dim]No decisions yet[/dim]")

        lines.append("")

        # ── Usage ────────────────────────────────────────────────
        lines.append("[bold]Usage[/bold]")
        lines.append("─" * 40)
        usage = session.get("usage") or {}
        active_secs = usage.get("active_seconds") or usage.get("compute_seconds", 0)
        output_tokens = usage.get("output_tokens", 0)
        input_tokens = usage.get("input_tokens", 0)
        # Rough cost estimate (claude-opus-4 pricing placeholder)
        cost = (input_tokens / 1_000_000 * 15 + output_tokens / 1_000_000 * 75)
        lines.append(f"  Active time : [bold]{active_secs}s[/bold]")
        lines.append(f"  Input tokens: [bold]{input_tokens:,}[/bold]")
        lines.append(f"  Output tokens: [bold]{output_tokens:,}[/bold]")
        if cost > 0:
            lines.append(f"  Est. cost   : [bold]${cost:.4f}[/bold]")

        self._content.update("\n".join(lines))
