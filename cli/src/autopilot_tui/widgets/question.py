"""Right-top Question tab widget."""

from __future__ import annotations

from textual.app import ComposeResult
from textual.message import Message
from textual.widget import Widget
from textual.widgets import Button, Input, Label, Static


class AnswerSubmitted(Message):
    def __init__(self, tool_use_id: str, answer: str) -> None:
        super().__init__()
        self.tool_use_id = tool_use_id
        self.answer = answer


class QuestionWidget(Widget):
    DEFAULT_CSS = """
    QuestionWidget {
        height: 100%;
        width: 100%;
        layout: vertical;
        padding: 1 2;
    }
    #q-body {
        height: 1fr;
        overflow-y: auto;
    }
    #q-input-row {
        height: auto;
        layout: horizontal;
        margin-top: 1;
    }
    #answer-input {
        width: 1fr;
    }
    #submit-btn {
        width: 12;
        margin-left: 1;
    }
    .option-btn {
        width: 100%;
        margin-bottom: 0;
        text-align: left;
    }
    """

    def __init__(self) -> None:
        super().__init__()
        self._tool_use_id: str = ""
        self._options: list[str] = []
        self._body_content = Static("")

    def compose(self) -> ComposeResult:
        yield self._body_content
        yield Label("[dim]Type answer or press a/b/c to select option:[/dim]", id="q-hint")
        with Widget(id="q-input-row"):
            yield Input(placeholder="Your answer…", id="answer-input")
            yield Button("Send ↵", id="submit-btn", variant="primary")

    def load_question(self, question: dict | None) -> None:
        if question is None:
            self._tool_use_id = ""
            self._options = []
            self._body_content.update("[dim]No pending question[/dim]")
            return

        self._tool_use_id = question.get("tool_use_id", "")
        self._options = question.get("options") or []

        lines: list[str] = []
        lines.append(f"[bold]{question.get('question', '')}[/bold]")
        lines.append("")
        ctx = question.get("context", "")
        if ctx:
            lines.append(f"[dim]{ctx}[/dim]")
            lines.append("")

        if self._options:
            letters = "abcdefghij"
            for i, opt in enumerate(self._options):
                if i < len(letters):
                    lines.append(f"  [{letters[i].upper()}] {opt}")
            lines.append("")

        self._body_content.update("\n".join(lines))

        # Clear previous answer
        try:
            inp = self.query_one("#answer-input", Input)
            inp.value = ""
        except Exception:
            pass

    def select_option(self, letter: str) -> None:
        """Pre-fill input with option text for a/b/c quick select."""
        letters = "abcdefghij"
        idx = letters.index(letter.lower()) if letter.lower() in letters else -1
        if 0 <= idx < len(self._options):
            try:
                inp = self.query_one("#answer-input", Input)
                inp.value = self._options[idx]
                inp.focus()
            except Exception:
                pass

    def _submit(self) -> None:
        if not self._tool_use_id:
            return
        try:
            inp = self.query_one("#answer-input", Input)
            answer = inp.value.strip()
            if answer:
                self.post_message(AnswerSubmitted(self._tool_use_id, answer))
                inp.value = ""
        except Exception:
            pass

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "submit-btn":
            self._submit()
            event.stop()

    def on_input_submitted(self, event: Input.Submitted) -> None:
        if event.input.id == "answer-input":
            self._submit()
            event.stop()
