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

    args = parser.parse_args()
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
