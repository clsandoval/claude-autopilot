---
name: remote-podcast
description: Use when generating a two-speaker podcast episode from mounted source material in a Managed Agent container. Pimsleur bilingual Japanese immersion activates via `[PIMSLEUR]` marker in the brief.
credentials:
  - name: ANTHROPIC_API_KEY
    check: env
    required: true
  - name: GEMINI_API_KEY
    check: env
    required: true
  - name: TELEGRAM_BOT_TOKEN
    check: env
    required: true
  - name: TELEGRAM_CHAT_ID
    check: env
    required: true
interview:
  - id: source_artifact
    prompt: "Path to the source artifact (spec, plan, doc) OR a topic brief?"
  - id: episode_name
    prompt: "Episode name / slug?"
  - id: duration
    prompt: "Target duration (e.g., '30 min', '60 min')?"
  - id: angle
    prompt: "One non-obvious thread or claim this episode should make?"
payload:
  - path: scripts/generate.sh
    required: true
  - path: scripts/verify-dialogue.py
    required: true
---

# Remote Podcast

Generate a two-speaker podcast from source material and mounted resources, then deliver via Telegram.

## Overview

Two friends co-investigating a topic — warm toward each other, skeptical toward the material. Dry humor, real disagreement, no AI-podcast hype. Pimsleur mode adds a Japanese language layer (see `podcast-pimsleur.md`).

Output: `dialogue.json`, a transcript, an MP3 from Gemini TTS, a Telegram send.

## Environment

- `source /workspace/.env` in every bash command
- Scripts may mount at `/workspace/` OR `/mnt/session/uploads/workspace/` — run `ls -R` on both to find paths
- Install once: `apt-get update && apt-get install -y ffmpeg jq curl python3-pip python3-yaml`

## Workflow

1. **Read the brief and ALL mounted resources.** `ls -R /mnt/session/uploads/ 2>/dev/null; ls -R /workspace/ 2>/dev/null`. For Pimsleur episodes, also read `japanese/schedule.yaml`, `japanese/profile.yaml`, and the `podcast-pimsleur.md` reference file.

2. **Plan the arc.** What is the ONE non-obvious thread or claim this episode makes? Structure around that — not a linear tour of the material.

3. **Draft `/tmp/dialogue.json`**:
   ```json
   [{"speaker": "a", "text": "..."}, {"speaker": "b", "text": "..."}]
   ```
   For Pimsleur episodes, follow `podcast-pimsleur.md` for exposure scaffolding, kana-vs-kanji, quoted Japanese, and ratio targets.

4. **Verify before generating audio:**
   ```bash
   # Non-Pimsleur
   python3 /workspace/verify-dialogue.py /tmp/dialogue.json

   # Pimsleur
   python3 /workspace/verify-dialogue.py /tmp/dialogue.json \
     --episode <N> \
     --schedule /workspace/japanese/schedule.yaml \
     --review-items "<comma-sep from brief>"
   ```
   If it fails, REWRITE the dialogue. Do NOT edit the script thresholds.

5. **Save transcript** to `podcasts/<name>-transcript.md` with `**A:**` / `**B:**` prefixes.

6. **Generate audio:**
   ```bash
   source /workspace/.env && bash /workspace/generate.sh /tmp/dialogue.json podcasts/<name>.mp3
   ```
   For dialogues ≥8000 words (≥50 min audio), prepend `PODCAST_BATCH_SIZE=4` to avoid late-batch TTS timeouts. Also drop to 4 if prosody sounds rushed on shorter episodes.

7. **Deliver via Telegram:**
   ```bash
   curl -s -X POST "https://api.telegram.org/bot${TELEGRAM_BOT_TOKEN}/sendAudio" \
     -F chat_id=${TELEGRAM_CHAT_ID} \
     -F audio=@"podcasts/<name>.mp3" \
     -F title="<title>" -F caption="<caption>"
   ```

   **Caption — Pimsleur episodes:** the caption MUST list every new vocab item and grammar pattern covered, with BOTH kanji and kana spellings plus the English meaning. Format each vocab line as `漢字 (かな) — meaning` and each grammar line as `〜pattern — meaning`. Group under `📚 New vocab:` and `📐 New grammar:` headings. If the caption exceeds Telegram's 1024-char limit, send the audio with a short caption, then follow with a `sendMessage` containing the full vocab/grammar list.

   **Caption — non-Pimsleur:** one-line summary.

8. **Pimsleur only:** write `/tmp/curriculum_update.yaml` per `podcast-pimsleur.md`. The orchestrator syncs it back to `schedule.yaml` / `vocabulary.yaml`.

9. **Commit** the transcript (NOT the .mp3) to branch `autopilot/podcast-ep<N>-<slug>` for Pimsleur, `autopilot/podcast-<slug>` otherwise. Push.

## Tone & voice

**Peg: Red Web / We Say Things.** Two knowledgeable friends co-investigating, dryly amused together. They like each other. They've been having this conversation for years. Dry humor comes from noticing things together, not from zingers at each other.

**Both speakers have expertise** — not expert/novice. A and B each bring a *different* angle of skepticism toward the material. The interesting thing is the collision of their takes.

**Default posture: skeptical pragmatism.** Assume claims in the source are overstated, under-specified, or won't survive contact with reality. Job: stress-test the material, not celebrate it. Required move when there's a claim to test:

**steelman → critique → calibrated close** ("works if X, fails if Y, testable by Z").

Pimsleur mode relaxes this when the topic is a vehicle for vocab, not a claim being tested (see `podcast-pimsleur.md`).

**Warm toward each other, skeptical toward the material.** Blunt about claims ("that's a press-release claim, not a technical one"); never sharp-edged at the other speaker ("read past the first sentence" — NO).

## Hard gates (enforced by `verify-dialogue.py`)

| Check | Rule | Failure |
|---|---|---|
| Speaker balance | A and B each 45–55% of words | Rewrite until balanced |
| Banned phrases | None of the 16 AI-tell phrases | Remove each |
| Sycophancy | ≤1 marker | Rewrite to drop compliments |
| Combat | 0 markers | Soften tone toward speaker |
| (Pimsleur) CJK floor | `ratio × words × 2` chars | Add more Japanese |
| (Pimsleur) CJK coverage | 30–95% of turns have Japanese (scales with ratio) | Distribute Japanese across turns |
| (Pimsleur) New vocab | Each item ≥3× (kanji OR reading matches) | Add exposures |
| (Pimsleur) New grammar | Each pattern ≥4× | Add uses in varied contexts |
| (Pimsleur) Review items | ≥10 distinct items present | Weave more review vocab in |

See `verify-dialogue.py` for the full grep lists and exact thresholds.

## Rationalization table — STOP if you catch yourself thinking these

| "This is fine because..." | Reality |
|---|---|
| "It's a technical topic, A should explain, B should ask" | B is an expert in an adjacent frame. Rewrite. |
| "The brief gave me a strong POV" | Interrogate it anyway. Premises are claims. |
| "I need enthusiasm to hook the listener" | Specificity hooks. "Brilliant" and "wild" are AI tells. |
| "Pushing back feels combative" | Warm pushback is the whole point. "Mm, is it really X?" |
| "Sharpening dialogue raises the stakes" | Stakes come from the material. Soften the edge. |
| "The Pimsleur ratio is just a vibe" | It's a character count, script-enforced. |
| "I can use kanji; readers know them" | TTS mispronounces kanji. Prefer kana. |
| "Three exposures clustered is fine" | Spaced repetition needs spacing. 20/50/80% marks. |
| "This curriculum item fits better than what's listed" | Do NOT substitute. `schedule.yaml` is verbatim. |
| "My dialogue is basically at ratio" | Run the script. Measure, don't estimate. |

## Red flags — STOP and rewrite

- "That's wild" / "tell me more" / "great point" / "brilliant" anywhere
- B's average turn length < 60% of A's
- Japanese items clustered in the first third
- Any explicit grammar lecture ("this is the conditional form")
- Celebration ending ("so excited to see where this goes")
- "Read past the first sentence," "I'll bring popcorn" — sharp edges at the other speaker
- A vocab item not in `schedule.yaml episode_<N>`
- Verification script not run, or run and edited thresholds to pass

All of these = rewrite, not ship.

## Audio defaults

- Model: `gemini-3.1-flash-tts-preview` (newest). Older `gemini-2.5-*` models are not better.
- Voices: Charon (A), Kore (B). Override via `PODCAST_GEMINI_VOICE_A/B`.
- Pace: natural — no `[fast]` tag. Override via `PODCAST_PACE` only if explicitly needed.
- Batch size: 8 default, 4 for long episodes or when prosody is rushed.

## What this skill does NOT do

- Does NOT write a summary. This is a conversation.
- Does NOT produce clean transitions ("speaking of which," "on that note").
- Does NOT make B a reaction machine.
- Does NOT ship without `verify-dialogue.py` passing.
