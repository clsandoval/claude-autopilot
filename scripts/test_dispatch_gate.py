"""Tests for dispatch-gate.py — the three-gate validator."""
import json
import os
import subprocess
import tempfile
import textwrap
from pathlib import Path

SCRIPT = Path(__file__).parent / "dispatch-gate.py"


def run_gate(*args, env=None):
    """Run dispatch-gate.py with args; return CompletedProcess."""
    return subprocess.run(
        ["python3", str(SCRIPT), *args],
        capture_output=True,
        text=True,
        env={**os.environ, **(env or {})},
    )


def write(path: Path, content: str) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(textwrap.dedent(content).lstrip("\n"))
    return path


def test_parse_manifest_extracts_three_sections(tmp_path):
    skill = write(tmp_path / "skill.md", """
        ---
        name: example
        credentials:
          - name: FOO
            check: env
            required: true
        interview:
          - id: topic
            prompt: "What's the topic?"
        payload:
          - path: scripts/tool.sh
            required: true
        ---

        # Skill body
        """)
    result = run_gate("parse-manifest", str(skill))
    assert result.returncode == 0, result.stderr
    assert "FOO" in result.stdout
    assert "topic" in result.stdout
    assert "scripts/tool.sh" in result.stdout


def test_check_brief_passes_with_both_files_non_empty(tmp_path):
    brief = tmp_path / "brief"
    write(brief / "outcome.md", "- [ ] Ship it\n")
    write(brief / "behavior.md", "Explore first, then commit.\n")
    result = run_gate("check-brief", str(brief))
    assert result.returncode == 0, result.stderr
    assert "PASS" in result.stdout


def test_check_brief_fails_if_outcome_missing(tmp_path):
    brief = tmp_path / "brief"
    write(brief / "behavior.md", "Something.\n")
    result = run_gate("check-brief", str(brief))
    assert result.returncode != 0
    assert "outcome.md" in result.stdout + result.stderr


def test_check_brief_fails_if_behavior_empty(tmp_path):
    brief = tmp_path / "brief"
    write(brief / "outcome.md", "- [ ] Ship\n")
    write(brief / "behavior.md", "\n   \n")
    result = run_gate("check-brief", str(brief))
    assert result.returncode != 0
    assert "behavior.md" in result.stdout + result.stderr
