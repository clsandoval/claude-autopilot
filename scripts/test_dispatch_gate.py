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


def test_check_payload_passes_when_all_files_exist(tmp_path):
    (tmp_path / "scripts").mkdir()
    (tmp_path / "scripts" / "tool.sh").write_text("#!/bin/sh\n")
    skill = write(tmp_path / "skill.md", """
        ---
        name: x
        payload:
          - path: scripts/tool.sh
            required: true
        ---
        """)
    brief = tmp_path / "brief"
    write(brief / "payload.json", '{"extra": []}')
    result = run_gate(
        "check-payload", str(skill), str(brief),
        env={"AUTOPILOT_SKILL_ROOT": str(tmp_path)},
    )
    assert result.returncode == 0, result.stderr
    assert "PASS" in result.stdout


def test_check_payload_fails_on_missing_required(tmp_path):
    skill = write(tmp_path / "skill.md", """
        ---
        name: x
        payload:
          - path: scripts/missing.sh
            required: true
        ---
        """)
    brief = tmp_path / "brief"
    write(brief / "payload.json", '{"extra": []}')
    result = run_gate(
        "check-payload", str(skill), str(brief),
        env={"AUTOPILOT_SKILL_ROOT": str(tmp_path)},
    )
    assert result.returncode != 0
    assert "missing.sh" in result.stdout + result.stderr


def test_check_payload_includes_extra_paths_from_payload_json(tmp_path):
    skill = write(tmp_path / "skill.md", """
        ---
        name: x
        payload: []
        ---
        """)
    doc = tmp_path / "some_doc.md"
    doc.write_text("hi")
    brief = tmp_path / "brief"
    write(brief / "payload.json", json.dumps({"extra": [str(doc)]}))
    result = run_gate(
        "check-payload", str(skill), str(brief),
        env={"AUTOPILOT_SKILL_ROOT": str(tmp_path)},
    )
    assert result.returncode == 0


def test_check_credentials_env_pass(tmp_path):
    skill = write(tmp_path / "skill.md", """
        ---
        name: x
        credentials:
          - name: FAKE_KEY
            check: env
            required: true
        ---
        """)
    result = run_gate("check-credentials", str(skill), env={"FAKE_KEY": "yes"})
    assert result.returncode == 0, result.stderr
    assert "FAKE_KEY" in result.stdout
    assert "PASS" in result.stdout


def test_check_credentials_env_fail(tmp_path):
    skill = write(tmp_path / "skill.md", """
        ---
        name: x
        credentials:
          - name: MISSING_KEY_XYZ
            check: env
            required: true
        ---
        """)
    clean = {k: v for k, v in os.environ.items() if k != "MISSING_KEY_XYZ"}
    result = subprocess.run(
        ["python3", str(SCRIPT), "check-credentials", str(skill)],
        capture_output=True, text=True, env=clean,
    )
    assert result.returncode != 0
    assert "MISSING_KEY_XYZ" in result.stdout + result.stderr


def test_check_credentials_file_pass(tmp_path):
    f = tmp_path / "thing.txt"
    f.write_text("x")
    skill = write(tmp_path / "skill.md", f"""
        ---
        name: x
        credentials:
          - name: {f}
            check: file
            required: true
        ---
        """)
    result = run_gate("check-credentials", str(skill))
    assert result.returncode == 0
