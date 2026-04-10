"""Right-top Artifacts tab widget."""

from __future__ import annotations

from textual.app import ComposeResult
from textual.widget import Widget
from textual.widgets import Static

from autopilot_tui.parser import Artifact, time_ago


class ArtifactsWidget(Widget):
    DEFAULT_CSS = """
    ArtifactsWidget {
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

    def update(self, artifacts: list[Artifact]) -> None:
        if not artifacts:
            self._content.update("[dim]No artifacts yet[/dim]")
            return

        lines: list[str] = []
        lines.append(f"[bold]{len(artifacts)} file(s) written[/bold]")
        lines.append("─" * 40)
        for artifact in artifacts:
            ts = time_ago(artifact.get("timestamp"))
            ts_str = f"  [dim]{ts}[/dim]" if ts else ""
            lines.append(f"  📄 {artifact['path']}{ts_str}")

        self._content.update("\n".join(lines))
