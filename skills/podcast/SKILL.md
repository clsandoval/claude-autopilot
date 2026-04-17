---
name: podcast
description: Use when turning any artifact (spec, plan, design doc, README, research notes) into a two-speaker podcast audio file. Triggers include "podcast", "make a podcast of", "turn this into a podcast", "podcast this spec".
---

# Podcast — Artifact-to-Audio

Convert a spec, plan, or design doc into a two-speaker podcast audio conversation.

## Overview

Two friends co-investigating the artifact — warm toward each other, skeptical toward the material. Dry humor, real disagreement, no AI-podcast hype.

Output: `dialogue.json`, a transcript, an MP3 from Gemini TTS. Run locally, no Telegram delivery by default (remote flow handles that).

## Invocation

```
/podcast <filepath>
```

The argument is a path to a markdown or text file.

## Workflow

1. **Read the artifact** at the given filepath.

2. **Identify the thread.** What is the ONE non-obvious claim or thesis this piece makes? Structure the episode around that — not a linear tour.

3. **Draft the dialogue** as a JSON array at `/tmp/dialogue.json`:
   ```json
   [{"speaker": "a", "text": "..."}, {"speaker": "b", "text": "..."}]
   ```

4. **Verify before generating audio:**
   ```bash
   python3 "${CLAUDE_PLUGIN_ROOT}/scripts/verify-dialogue.py" /tmp/dialogue.json
   ```
   If it fails, REWRITE the dialogue. Do NOT edit the script thresholds.

5. **Save transcript** to `podcasts/<name>-transcript.md` (create `podcasts/` if needed) with `**A:**` / `**B:**` prefixes. `<name>` derived from the input filename (strip extension).

6. **Generate audio:**
   ```bash
   bash "${CLAUDE_PLUGIN_ROOT}/scripts/generate.sh" /tmp/dialogue.json podcasts/<name>.mp3
   ```
   For dialogues ≥8000 words, prepend `PODCAST_BATCH_SIZE=4` to avoid late-batch TTS timeouts. Also drop to 4 if prosody sounds rushed.

7. **Report** to the user: audio path, duration, transcript path, and a one-liner about what the hosts made of the artifact.

## Tone & voice

**Peg: Red Web / We Say Things.** Two knowledgeable friends co-investigating, dryly amused together. They like each other. They've been having this conversation for years. Dry humor comes from noticing things together, not from zingers at each other.

**Both speakers have expertise** — not expert/novice. A and B each bring a *different* angle of skepticism. The interesting thing is the collision of their takes.

**Default posture: skeptical pragmatism.** Assume claims in the artifact are overstated, under-specified, or won't survive contact with reality. Job: stress-test the material, not celebrate it.

Required move: **steelman → critique → calibrated close** ("works if X, fails if Y, testable by Z").

**Warm toward each other, skeptical toward the material.** Blunt about claims ("that's a press-release claim, not a technical one"); never sharp-edged at the other speaker ("read past the first sentence" — NO).

## Dialogue length

- ~1 min audio per 500 words of input.
- 150 words of dialogue per minute of audio.
- 1000-word spec → ~2 min episode. 3000-word doc → ~6 min.

## Hard gates (enforced by `verify-dialogue.py`)

| Check | Rule | Failure |
|---|---|---|
| Speaker balance | A and B each 45–55% of words | Rewrite until balanced |
| Banned phrases | None of the 16 AI-tell phrases | Remove each |
| Sycophancy | ≤1 marker | Rewrite to drop compliments |
| Combat | 0 markers | Soften tone toward speaker |

The script exits non-zero on failure with a punch list. Fix the dialogue, re-run.

## Rationalization table — STOP if you catch yourself thinking these

| "This is fine because..." | Reality |
|---|---|
| "It's a technical topic, A should explain, B should ask" | B is an expert in an adjacent frame. Rewrite. |
| "The artifact has a strong POV" | Interrogate it anyway. Premises are claims. |
| "I need enthusiasm to hook the listener" | Specificity hooks. "Brilliant" and "wild" are AI tells. |
| "Pushing back feels combative" | Warm pushback is the whole point. "Mm, is it really X?" |
| "Sharpening dialogue raises the stakes" | Stakes come from the material. Soften the edge. |
| "Short spec, I'll just summarize it" | Summary ≠ conversation. Find the thread, argue it. |
| "Verification script is overkill for this" | Run it anyway. 5 seconds, catches real issues. |

## Red flags — STOP and rewrite

- "That's wild" / "tell me more" / "great point" / "brilliant" anywhere
- B's average turn length < 60% of A's
- Any "Host:" / "Guest:" / "Interviewer:" labels
- Celebration ending ("so excited to see where this goes")
- Linear tour of the spec instead of one thesis
- "Read past the first sentence," "I'll bring popcorn" — sharp edges at the other speaker
- Verification script not run, or run and edited thresholds to pass

All of these = rewrite, not ship.

## Audio defaults

- Model: `gemini-3.1-flash-tts-preview`. Older `gemini-2.5-*` aren't better.
- Voices: Charon (A), Kore (B). Override via `PODCAST_GEMINI_VOICE_A/B`.
- Pace: natural — no `[fast]` tag. Override via `PODCAST_PACE` only if explicitly needed.
- Batch size: 8 default, 4 for long or rushed-sounding episodes.
- Requires `GOOGLE_API_KEY`, `ffmpeg`, `jq`, `curl` on the local machine.

## Output

All files go to `podcasts/` in the current working directory:
- `<name>.mp3` — podcast audio
- `<name>-transcript.md` — readable dialogue

Do NOT commit the audio or transcript — the user decides what to do with them.

## What this skill does NOT do

- Does NOT write a summary. This is a conversation.
- Does NOT produce clean transitions ("speaking of which," "on that note").
- Does NOT make B a reaction machine.
- Does NOT ship without `verify-dialogue.py` passing.
- Does NOT commit artifacts.
