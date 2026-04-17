#!/usr/bin/env python3
"""Pre-submit verification for podcast dialogue.json.

Non-Pimsleur episode:
    python3 verify-dialogue.py /tmp/dialogue.json

Pimsleur episode:
    python3 verify-dialogue.py /tmp/dialogue.json \\
        --episode 5 \\
        --schedule /workspace/japanese/schedule.yaml \\
        --review-items "食べる,難しい,会社,..."

Exits 0 on success, 1 on failure with a punch-list of issues.
"""

from __future__ import annotations

import argparse
import json
import re
import sys

BANNED_PHRASES = [
    "that's wild", "tell me more", "yeah exactly", "honestly", "genuinely",
    "literally", "100%", "okay so", "right? right?", "love that",
    "that's fascinating", "wait what", "no way", "shut up",
    "mind blown", "big if true",
]

SYCOPHANCY_MARKERS = [
    "good point", "great point", "fair point", "that's a good",
    "you're right about", "you nailed it", "exactly what i",
    "brilliant", "really cool", "so cool", "super cool",
    "love how you", "love that you", "this is such",
    "really well put", "couldn't have said", "nailed",
]

COMBAT_MARKERS = [
    "read past", "read the docs", "you're wrong", "you are wrong",
    "let me rephrase", "next time", "i'll bring popcorn",
    "go pitch it", "that's not architecture", "reinvented",
    "learn to read", "that's just", "obviously you",
]

CJK_RE = re.compile(r"[\u3040-\u30ff\u4e00-\u9fff]")
JP_SPAN_RE = re.compile(r"[\u3040-\u30ff\u4e00-\u9fff][\u3040-\u30ff\u4e00-\u9fff\u3001\u3002\uff01\uff1f\s]*")


def check_jp_en_pairing(dialogue: list[dict]) -> tuple[int, int, list[str]]:
    """For every Japanese span, require an explicit structural gloss signal.

    Paired if one of these patterns surrounds the JP span:
      - AFTER: quote/comma then em-dash then English word    `"JP" — compare`
      - AFTER: parenthetical English                         `"JP" (compare)`
      - AFTER: marker word                                   `"JP" means compare` / `that is` / `i.e.` / `in other words`
      - BEFORE: English word then em-dash then JP            `compare — "JP"`
      - BEFORE: English word then colon/comma then JP        `compare, "JP"` / `compare: "JP"`

    Bare substitution (`"JP" のが today's job`) is NOT paired — that's the
    failure mode this check exists to prevent.

    Returns (total_spans, unpaired_count, sample_unpaired_contexts).
    """
    total = 0
    unpaired = []
    after_signal = re.compile(
        r"""^
            (
              ["'」』\s,.!?]*[—\-–]\s*[A-Za-z]            # em-dash then English
              | ["'」』]?\s*\(\s*[A-Za-z]                   # parenthetical English
              | ["'」』\s,]*\b(means|that\ is|i\.e\.|in\ other\ words)\b
            )""", re.I | re.X,
    )
    # e.g. `compare — "JP"` or `compare, "JP"` or `compare: "JP"`
    before_signal = re.compile(
        r"""[A-Za-z]{3,}\s*[—\-–,:;]\s*["'「『]?\s*$""", re.X,
    )
    for turn in dialogue:
        t = turn.get("text", "")
        for m in JP_SPAN_RE.finditer(t):
            jp = m.group(0).strip()
            if not jp or not CJK_RE.search(jp):
                continue
            total += 1
            pre = t[max(0, m.start() - 40): m.start()]
            post = t[m.end(): m.end() + 40]
            paired = bool(after_signal.search(post)) or bool(before_signal.search(pre))
            if not paired:
                ctx = (pre[-25:] + "«" + jp + "»" + post[:25]).replace("\n", " ")
                unpaired.append(ctx)
    return total, len(unpaired), unpaired[:10]


def load_schedule_episode(schedule_path: str, episode: int) -> dict:
    import yaml  # lazy import so non-Pimsleur runs don't need pyyaml
    sched = yaml.safe_load(open(schedule_path))
    key = f"episode_{episode}"
    if key not in sched:
        raise SystemExit(f"FAIL: {key} not found in {schedule_path}")
    return sched[key]


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("dialogue", help="Path to dialogue.json")
    ap.add_argument("--episode", type=int, help="Pimsleur episode number")
    ap.add_argument("--schedule", help="Path to schedule.yaml (required with --episode)")
    ap.add_argument("--review-items", default="",
                    help="Comma-separated review items from the brief")
    ap.add_argument("--min-review-present", type=int, default=10,
                    help="Minimum distinct review items that must appear (default 10)")
    ap.add_argument("--max-unpaired-pct", type=float, default=0.20,
                    help="Max fraction of JP spans without English gloss (default 0.20)")
    args = ap.parse_args()

    d = json.load(open(args.dialogue))
    a = [t["text"] for t in d if t.get("speaker") == "a"]
    b = [t["text"] for t in d if t.get("speaker") == "b"]
    wa = sum(len(t.split()) for t in a)
    wb = sum(len(t.split()) for t in b)
    total = wa + wb
    n_turns = len(a) + len(b)
    all_text = " ".join(a + b)
    lower = all_text.lower()

    if total == 0:
        print("FAIL: EMPTY DIALOGUE")
        sys.exit(1)

    cjk = len(CJK_RE.findall(all_text))
    turns_with_cjk = sum(1 for t in a + b if CJK_RE.search(t))
    fails: list[str] = []

    # --- tone gates (apply to every episode) ---

    a_pct = wa / total
    if not (0.45 <= a_pct <= 0.55):
        fails.append(f"BALANCE: A is {100*a_pct:.1f}% (must be 45–55%)")

    banned_hits = sorted({p for p in BANNED_PHRASES if p in lower})
    if banned_hits:
        fails.append(f"BANNED PHRASES: {banned_hits}")

    syco_hits = [m for m in SYCOPHANCY_MARKERS if m in lower]
    if len(syco_hits) > 1:
        fails.append(f"SYCOPHANCY: {syco_hits}")

    combat_hits = [m for m in COMBAT_MARKERS if m in lower]
    if combat_hits:
        fails.append(f"COMBAT: {combat_hits} — soften, warm toward speaker, skeptical toward material")

    print(f"Words: {total}  A={wa} ({100*a_pct:.1f}%)  B={wb} ({100*wb/total:.1f}%)")
    print(f"Turns: {n_turns}  A={len(a)} avg {wa/max(len(a),1):.0f}w  "
          f"B={len(b)} avg {wb/max(len(b),1):.0f}w")
    print(f"CJK chars: {cjk}  Turns with CJK: {turns_with_cjk}")
    print(f"Banned: {len(banned_hits)}  Sycophancy: {len(syco_hits)}  Combat: {len(combat_hits)}")

    # --- Pimsleur gates ---

    if args.episode is not None:
        if not args.schedule:
            print("FAIL: --episode requires --schedule")
            sys.exit(1)

        ep = load_schedule_episode(args.schedule, args.episode)
        ratio = float(ep.get("japanese_ratio", 0))
        vocab_items = [(v["word"], v.get("reading", v["word"]))
                       for v in ep.get("vocab", [])]
        # Normalise grammar patterns (curricula often store with leading 〜)
        grammar_items = [g["pattern"].lstrip("〜") for g in ep.get("grammar", [])]
        review_items = [x.strip() for x in args.review_items.split(",") if x.strip()]

        min_cjk = int(ratio * total * 2)
        # Turn coverage: 30% at ratio 0.20, 90% at 0.60, capped at 95%
        min_turn_pct = min(0.30 + (ratio - 0.20) * 1.5, 0.95) if ratio > 0 else 0
        turn_pct = turns_with_cjk / n_turns

        print(f"Pimsleur: ratio={ratio}  min_cjk={min_cjk}  "
              f"min_turn_coverage={min_turn_pct:.0%}  actual_coverage={turn_pct:.0%}")

        if cjk < min_cjk:
            fails.append(f"CJK FLOOR: {cjk} < {min_cjk} (need {min_cjk - cjk} more kana/kanji)")
        if turn_pct < min_turn_pct:
            fails.append(
                f"CJK COVERAGE: {turn_pct:.0%} of turns have Japanese (need {min_turn_pct:.0%}) "
                "— sprinkle Japanese across more turns, not just a few"
            )

        # Pairing check: every JP span must have an English gloss nearby
        total_spans, unpaired_count, samples = check_jp_en_pairing(d)
        unpaired_pct = unpaired_count / max(total_spans, 1)
        print(f"JP-EN pairing: {total_spans - unpaired_count}/{total_spans} spans paired "
              f"({(1-unpaired_pct):.0%})  max_unpaired={args.max_unpaired_pct:.0%}")
        if unpaired_pct > args.max_unpaired_pct:
            msg = (
                f"JP-EN PAIRING: {unpaired_count}/{total_spans} spans ({unpaired_pct:.0%}) "
                f"have no English gloss within ±50 chars (max {args.max_unpaired_pct:.0%}). "
                f"Add em-dash paraphrases (`\"JP\" — english —`) or parentheticals "
                f"(`\"JP\" (english)`). Examples:\n    " + "\n    ".join(samples)
            )
            fails.append(msg)

        # Vocab: each item must appear ≥3× — kanji OR reading both count
        for word, reading in vocab_items:
            n = all_text.count(word) + (
                all_text.count(reading) if reading != word else 0
            )
            if n < 3:
                fails.append(f"NEW VOCAB: '{word}' ({reading}) appears {n}× (need ≥3)")

        # Grammar: each pattern must appear ≥4×
        for pattern in grammar_items:
            n = all_text.count(pattern)
            if n < 4:
                fails.append(f"NEW GRAMMAR: '{pattern}' appears {n}× (need ≥4)")

        # Review: ≥ min_review_present distinct items present
        if review_items:
            present = [w for w in review_items if all_text.count(w) > 0]
            if len(present) < args.min_review_present:
                fails.append(
                    f"REVIEW: only {len(present)}/{len(review_items)} present "
                    f"(need ≥{args.min_review_present})"
                )

    if fails:
        print("\nFAILED CHECKS:")
        for f in fails:
            print(f"  - {f}")
        sys.exit(1)

    print("\nOK — ready for audio")


if __name__ == "__main__":
    main()
