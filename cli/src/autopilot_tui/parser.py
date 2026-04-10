"""Parse raw Managed Agent events into structured data."""

from __future__ import annotations

import re
from datetime import datetime, timezone
from typing import TypedDict


class Phase(TypedDict):
    name: str
    status: str  # "complete" | "active" | "pending"
    started_at: str | None
    ended_at: str | None


class Decision(TypedDict):
    text: str
    timestamp: str | None


class Artifact(TypedDict):
    path: str
    timestamp: str | None


class Question(TypedDict):
    tool_use_id: str
    question: str
    context: str
    options: list[str]


# Canonical phase names used in agent messages
_KNOWN_PHASES = [
    "Exploration & Brainstorming",
    "Spec",
    "Planning",
    "Implementation",
    "Completion",
]

_PHASE_RE = re.compile(r"##\s*Phase\s+(\d+)[:\s]*(.*)", re.IGNORECASE)
_DECISION_RE = re.compile(r"^\s*Decision:\s*(.+)", re.MULTILINE)


def _event_text(event: dict) -> str:
    """Extract plaintext from event content."""
    content = event.get("content", [])
    if isinstance(content, str):
        return content
    parts = []
    for block in content:
        if isinstance(block, dict) and block.get("type") == "text":
            parts.append(block.get("text", ""))
    return "\n".join(parts)


def _ts(event: dict) -> str | None:
    return event.get("created_at") or event.get("timestamp")


def extract_phases(events: list[dict]) -> list[Phase]:
    """Return phase list derived from agent messages."""
    found: dict[str, Phase] = {}
    ordered: list[str] = []

    for event in events:
        if event.get("type") != "agent.message":
            continue
        text = _event_text(event)
        for match in _PHASE_RE.finditer(text):
            num = match.group(1)
            raw_name = match.group(2).strip()
            # Normalise to known name if possible
            name = raw_name
            try:
                idx = int(num) - 1
                if 0 <= idx < len(_KNOWN_PHASES):
                    name = f"Phase {num}: {_KNOWN_PHASES[idx]}"
            except ValueError:
                pass
            if name not in found:
                found[name] = Phase(
                    name=name,
                    status="active",
                    started_at=_ts(event),
                    ended_at=None,
                )
                ordered.append(name)
            else:
                # Later mention → still active / update timestamp
                found[name]["started_at"] = found[name]["started_at"] or _ts(event)

    # Mark all but the last as complete
    result: list[Phase] = []
    for i, name in enumerate(ordered):
        phase = found[name].copy()
        if i < len(ordered) - 1:
            phase["status"] = "complete"
        result.append(phase)

    return result


def extract_decisions(events: list[dict]) -> list[Decision]:
    decisions: list[Decision] = []
    for event in events:
        if event.get("type") != "agent.message":
            continue
        text = _event_text(event)
        for match in _DECISION_RE.finditer(text):
            decisions.append(
                Decision(text=match.group(1).strip(), timestamp=_ts(event))
            )
    return decisions


def extract_artifacts(events: list[dict]) -> list[Artifact]:
    artifacts: list[Artifact] = []
    seen_paths: set[str] = set()
    for event in events:
        if event.get("type") != "agent.tool_use":
            continue
        name = event.get("name", "")
        if name != "write":
            continue
        inp = event.get("input") or {}
        path = inp.get("file_path") or inp.get("path", "")
        if path and path not in seen_paths:
            seen_paths.add(path)
            # Strip workspace prefix for readability
            display_path = path.replace("/workspace/repo/", "")
            ts = event.get("processed_at") or _ts(event)
            artifacts.append(Artifact(path=display_path, timestamp=ts))
    return artifacts


def extract_question(events: list[dict]) -> Question | None:
    """Return the last unanswered ask_user question, or None."""
    last_question: Question | None = None
    answered_ids: set[str] = set()

    for event in events:
        etype = event.get("type", "")
        if etype == "agent.custom_tool_use" and event.get("name") == "ask_user":
            inp = event.get("input", {})
            last_question = Question(
                tool_use_id=event.get("id", ""),
                question=inp.get("question", ""),
                context=inp.get("context", ""),
                options=inp.get("options") or [],
            )
        elif etype == "user.custom_tool_result":
            tool_use_id = event.get("tool_use_id", "")
            if tool_use_id:
                answered_ids.add(tool_use_id)

    if last_question and last_question["tool_use_id"] in answered_ids:
        return None
    return last_question


def is_blocked(events: list[dict]) -> bool:
    """True if the session is waiting for a tool result."""
    last_status: str | None = None
    last_stop_type: str | None = None

    for event in events:
        etype = event.get("type", "")
        if etype == "session.status_idle":
            last_status = "idle"
            stop = event.get("stop_reason") or {}
            last_stop_type = stop.get("type")
        elif etype == "session.status_running":
            last_status = "running"
            last_stop_type = None

    return last_status == "idle" and last_stop_type == "requires_action"


def session_status(session: dict, events: list[dict]) -> str:
    """Return display status string for a session."""
    raw = (session.get("status") or "").lower()
    if raw in ("complete", "completed", "done"):
        return "done"
    if raw in ("error", "failed"):
        return "error"
    if events and is_blocked(events):
        return "blocked"
    if raw in ("running", "active"):
        return "running"
    # Fall back to raw or 'done' for terminal states
    return raw or "done"


def format_event_line(event: dict) -> tuple[str, str] | None:
    """Return (css_class, display_text) for an event, or None to skip."""
    etype = event.get("type", "")
    ts = event.get("processed_at") or _ts(event)
    time_str = ""
    if ts:
        try:
            dt = datetime.fromisoformat(ts.replace("Z", "+00:00"))
            time_str = dt.astimezone(tz=None).strftime("%H:%M")
        except Exception:
            pass

    prefix = f"[{time_str}] " if time_str else ""

    if etype == "agent.message":
        text = _event_text(event)
        if not text.strip():
            return None
        first_line = text.strip().split("\n")[0][:120]
        if _PHASE_RE.search(first_line):
            return ("event-phase", f"{prefix}▶ {first_line}")
        return ("event-line", f"{prefix}{first_line[:100]}")

    if etype == "agent.custom_tool_use":
        name = event.get("name", "")
        if name == "ask_user":
            inp = event.get("input", {})
            q = inp.get("question", "")[:80]
            return ("event-question", f"{prefix}❓ {q}")
        return ("event-line", f"{prefix}⚙ custom: {name}")

    if etype == "user.custom_tool_result":
        content = event.get("content", [])
        if isinstance(content, list) and content:
            text = content[0].get("text", "")[:60] if isinstance(content[0], dict) else str(content[0])[:60]
        else:
            text = str(content)[:60]
        return ("event-line", f"{prefix}↩ answer: {text}")

    if etype == "agent.tool_use":
        name = event.get("name", "")
        inp = event.get("input", {})
        detail = ""
        if name == "bash":
            detail = (inp.get("command") or "")[:60]
        elif name in ("read", "write", "edit", "glob", "grep"):
            detail = (inp.get("file_path") or inp.get("path") or inp.get("pattern") or "")[:60]
        else:
            detail = name
        return ("event-line", f"{prefix}⚙ {name}: {detail}")

    if etype == "session.status_running":
        return ("event-line", f"{prefix}● session running")

    if etype == "session.status_idle":
        stop = event.get("stop_reason", {})
        stop_type = stop.get("type", "")
        if stop_type == "requires_action":
            return ("event-question", f"{prefix}◆ session blocked — waiting for input")
        return ("event-line", f"{prefix}○ session idle ({stop_type})")

    if etype == "session.status_terminated":
        return ("event-line", f"{prefix}✕ session terminated")

    # Skip noise: span.*, agent.thinking, agent.tool_result, etc.
    return None


def time_ago(ts: str | None) -> str:
    if not ts:
        return ""
    try:
        dt = datetime.fromisoformat(ts.replace("Z", "+00:00"))
        now = datetime.now(tz=timezone.utc)
        secs = int((now - dt).total_seconds())
        if secs < 60:
            return f"{secs}s ago"
        if secs < 3600:
            return f"{secs // 60}m ago"
        if secs < 86400:
            return f"{secs // 3600}h ago"
        return f"{secs // 86400}d ago"
    except Exception:
        return ""
