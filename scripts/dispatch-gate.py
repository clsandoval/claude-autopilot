#!/usr/bin/env python3
"""Validate the three autopilot dispatch gates.

Subcommands:
  parse-manifest <skill.md>         Print credentials/interview/payload from frontmatter
  check-brief <brief-dir>           Validate outcome.md and behavior.md non-empty
  check-payload <skill.md> <brief-dir>   Validate every payload file exists (skill payload + context)
  check-credentials <skill.md>      Run every credentials check; print pass/fail table
  all <skill.md> <brief-dir>        Run all checks; exit non-zero on any hard failure
"""
import argparse
import json
import os
import re
import sys
from pathlib import Path


def parse_frontmatter(path: Path) -> dict:
    text = path.read_text()
    m = re.match(r"^---\n(.*?)\n---\n", text, re.DOTALL)
    if not m:
        return {}
    import yaml
    return yaml.safe_load(m.group(1)) or {}


def cmd_parse_manifest(args) -> int:
    fm = parse_frontmatter(Path(args.skill))
    print(json.dumps({
        "credentials": fm.get("credentials", []),
        "interview": fm.get("interview", []),
        "payload": fm.get("payload", []),
    }, indent=2))
    return 0


def cmd_check_credentials(args) -> int:
    fm = parse_frontmatter(Path(args.skill))
    rows = []
    hard_fail = False
    for entry in fm.get("credentials", []) or []:
        name = entry.get("name")
        check = entry.get("check", "env")
        required = bool(entry.get("required", True))
        if check == "env":
            ok = bool(os.environ.get(name))
            reason = "" if ok else "env var not set"
        elif check == "file":
            ok = Path(name).exists()
            reason = "" if ok else "file not found"
        elif check == "remote-secret":
            ok = True
            reason = "manual (remote-secret — verify in remote env)"
        else:
            ok = False
            reason = f"unknown check type: {check}"
        rows.append((name, check, "PASS" if ok else "FAIL", reason, required))
        if not ok and required:
            hard_fail = True

    width = max((len(r[0]) for r in rows), default=10)
    print(f"{'name'.ljust(width)}  check          status  note")
    for name, check, status, reason, req in rows:
        print(f"{name.ljust(width)}  {check.ljust(14)} {status}    {reason}")
    return 1 if hard_fail else 0


def cmd_check_payload(args) -> int:
    skill_path = Path(args.skill).resolve()
    fm = parse_frontmatter(skill_path)
    skill_root = Path(os.environ.get("AUTOPILOT_SKILL_ROOT", skill_path.parent))
    brief_dir = Path(args.brief_dir)

    failures = []
    checked = []

    for entry in fm.get("payload", []) or []:
        rel = entry.get("path")
        required = bool(entry.get("required", True))
        full = skill_root / rel
        checked.append(str(full))
        if not full.exists() and required:
            failures.append(f"skill payload missing: {rel}")

    payload_json = brief_dir / "payload.json"
    if payload_json.exists():
        data = json.loads(payload_json.read_text())
        for extra in data.get("extra", []) or []:
            checked.append(extra)
            if not Path(extra).exists():
                failures.append(f"extra payload missing: {extra}")

    if failures:
        for f in failures:
            print(f"FAIL: {f}")
        return 1
    print(f"PASS: {len(checked)} payload file(s) resolvable")
    for c in checked:
        print(f"  - {c}")
    return 0


def cmd_check_brief(args) -> int:
    brief_dir = Path(args.brief_dir)
    required = ["outcome.md", "behavior.md"]
    failures = []
    for name in required:
        p = brief_dir / name
        if not p.exists():
            failures.append(f"{name}: MISSING")
            continue
        if not p.read_text().strip():
            failures.append(f"{name}: EMPTY")
    if failures:
        for f in failures:
            print(f"FAIL: {f}")
        return 1
    print("PASS: outcome.md and behavior.md present and non-empty")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="cmd", required=True)

    p = sub.add_parser("parse-manifest")
    p.add_argument("skill")
    p.set_defaults(func=cmd_parse_manifest)

    p = sub.add_parser("check-brief")
    p.add_argument("brief_dir")
    p.set_defaults(func=cmd_check_brief)

    p = sub.add_parser("check-payload")
    p.add_argument("skill")
    p.add_argument("brief_dir")
    p.set_defaults(func=cmd_check_payload)

    p = sub.add_parser("check-credentials")
    p.add_argument("skill")
    p.set_defaults(func=cmd_check_credentials)

    args = parser.parse_args()
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
