---
name: remote-podcast
description: "Generate podcast audio from source material with optional Pimsleur bilingual Japanese immersion mode."
---

# Remote Podcast — Artifact-to-Audio (Managed Agent Version)

Runs inside a Managed Agent container. Generate a podcast from source material provided via the brief and mounted resources, then deliver via Telegram.

## Environment

- `source /workspace/.env` at the start of EVERY bash command (separate shells)
- Audio script at `/workspace/generate.sh` (or `/mnt/session/uploads/workspace/generate.sh` — check both)
- Install deps: `apt-get update && apt-get install -y ffmpeg jq curl python3-pip`
- `chmod +x /workspace/generate.sh`

## Personas — the two speakers are NOT an expert/novice pair

This is the single most common failure mode. Agents default to A-explains-B-reacts and produce a sycophantic lecture. Reject that framing.

**Both A and B have expertise. They have DIFFERENT perspectives on the same topic.** The interesting thing is the collision of their takes, not one teaching the other.

- **Person A** — has one angle (e.g. the builder, the insider, the optimist)
- **Person B** — has a different angle (e.g. the skeptic, the outsider with adjacent expertise, the pragmatist)

B is not a prompt-machine. B pushes back. B brings their own examples. B sometimes takes the conversation somewhere A didn't anticipate. B is sometimes RIGHT and A has to concede.

If the brief describes the speakers as expert/novice, reinterpret it — make B an expert in something adjacent that illuminates the topic from a different direction.

## Style

- Two friends riffing at a bar, not an interview. They interrupt, tangent, circle back.
- Short sentences. False starts. "Wait, no — actually..." Self-correction mid-sentence.
- Humor comes from specificity, not setups and punchlines.
- Blunt: dumb things are called dumb.

## Banned phrases (AI-dialogue crutches)

The agent MUST grep the dialogue for these and remove/rewrite. If any remain at verification time, the dialogue fails the pre-submit check:

- "that's wild"
- "tell me more"
- "yeah exactly"
- "honestly"
- "genuinely"
- "literally"
- "100%"
- "okay so"
- "right? right?"
- "love that"
- "that's fascinating"

(`"interesting"` is a weak tell but skipped by the auto-check because it produces false positives in compound phrases — watch for it manually.)

These are the tells. Real people don't talk like this; they use specific reactions tied to what was just said.

## Default posture: pragmatic, pessimism-leaning, steelman-first

The speakers' default orientation to the source material is **skeptical pragmatism**. Assume most ideas/plans/features the brief describes are either (a) overstated, (b) under-specified, or (c) probably won't survive contact with reality. The episode's job is to stress-test the material, not celebrate it.

**This is NOT cynicism or snark.** Dismissive pessimism ("this is dumb, next") is just as lazy as sycophancy — it avoids engagement. The required move is **steelman → critique**:

1. **Steelman first.** For every major claim in the brief, have one speaker articulate the strongest honest version of it — the version the original author *wishes* they'd written. This is non-negotiable. No critique is allowed to land before the steelman exists.
2. **Then critique.** Attack the steelmanned version, not a strawman. Identify: what assumptions does this rely on? What breaks it? What's the cheapest version that achieves 80% of the value, and why isn't *that* the plan? Where's the evidence this hasn't been tried before and failed?
3. **End with a calibrated position.** Not "everything's great" and not "everything's doomed." A specific call: "this works if X, falls over if Y, and you'll know within Z weeks."

Pragmatic pessimism means: assume schedules slip, assume the demo doesn't generalize, assume the clever architecture has a hidden cost, assume the user research is thin, assume the competitive moat is smaller than claimed. Demand evidence before belief. Treat enthusiasm in the source material as a yellow flag, not a green light.

Concrete language cues (use these shapes of sentence):
- "Okay, steelman first: the reason someone would build it this way is ..."
- "What's the cheapest experiment that would kill this idea? Has anyone run it?"
- "This works if [specific load-bearing assumption]. What happens when that breaks?"
- "I've seen this exact pattern before — [specific prior example] — and it failed because [specific reason]. What's different here?"
- "The press-release version of this is X. The boring version is Y. Which one is actually in the repo?"

## Anti-sycophancy guard

Sycophancy is the default failure mode of AI-written dialogue. It doesn't show up as obvious flattery — it shows up as:

- **Total agreement with the source material.** Every claim the brief makes is repeated approvingly. Every feature is "actually really clever." Nothing is weak, hand-wavy, unconvincing, or dumb.
- **B validates A's every point.** Even the disagreements are soft — "I mean, that's a fair point, but maybe..."
- **Compliment loops.** "That's such a good way of putting it." "You're totally right about that." "I love how you framed that."
- **Treating ordinary facts as profound.** Nodding along at statements that are, actually, kind of boring or obvious.
- **No stakes, no claims at risk.** Nobody is wrong, nobody updates, nothing lands with consequence.

Structural rules to fight this:

1. **At least one claim from the source material must be called out as weak, unconvincing, overstated, or suspect.** A or B (ideally B) reads the primary material critically, not as a fan. Example: "Okay, but the README says the adversarial benchmark 'refuses to fit garbage data.' That's a press release, not a technical claim. What does 'refuses' mean in the actual code? I couldn't find a check that does that."
2. **At least one moment where a speaker is provably wrong and gets corrected.** Not "good point" — actually wrong and they say "oh — wait, yeah, you're right, I was thinking of something else."
3. **At least one moment of genuine confusion.** Speaker admits they don't understand something. Doesn't pretend.
4. **Neither speaker is allowed to be the hype person.** If A is presenting the material, A must also be the first to point out its weaknesses. If B is pushing back, B must also concede when A actually has the better argument.
5. **No compliments on the topic itself.** Not "this is such a cool project," not "that's a brilliant architecture." The content should be interesting enough that you don't need to say it's interesting.
6. **No compliments between speakers.** They can laugh, they can concede, they can be surprised — but they never tell each other they made a good point.
7. **If the brief gives a strong POV, the speakers should still interrogate it.** Don't accept premises uncritically just because the brief asserts them.

Operational check for sycophancy during verification:

```bash
python3 <<'PY'
import json, re
d = json.load(open("/tmp/dialogue.json"))
text = " ".join(t["text"] for t in d).lower()
sycophancy_markers = [
    "good point", "great point", "fair point", "that's a good",
    "you're right about", "you nailed it", "exactly what i",
    "brilliant", "really cool", "so cool", "super cool",
    "love how you", "love that you", "this is such",
    "really well put", "couldn't have said", "nailed",
]
hits = [m for m in sycophancy_markers if m in text]
print(f"Sycophancy markers: {len(hits)} — {hits}")
if len(hits) > 1:
    print("FAIL: sycophancy guard triggered")
PY
```

More than 1 hit = rewrite.

## Required moments

Every episode MUST contain AT LEAST:

- **2 explicit steelmans** — one speaker articulates the strongest version of a claim (ideally a claim they're about to critique). Signal phrase: "steelman this for me" / "okay, best case for this is..." / "the strongest version of that argument is..."
- **3 disagreements** — substantive pushback, not "hmm are you sure"
- **2 "what breaks this"** — speaker names a specific failure mode, load-bearing assumption, or prior art that killed a similar attempt
- **2 self-corrections** — speaker changes their mind mid-sentence or backs off a claim
- **2 interruption recoveries** — one cuts the other off, then they recover the thread
- **1 concession** — A or B admits the other is right about something
- **1 tangent** — they wander off-topic for 4+ turns then one of them pulls it back
- **1 moment they're both fired up about the same thing** — preferably agreeing that something is *broken*, not that something is great
- **1 "wait, go back"** — B catches something A glossed over
- **1 calibrated closing position** — not "this is great" and not "this is doomed"; a specific "works if X, fails if Y, testable by Z"

These aren't nice-to-haves; they're the checksum that distinguishes real conversation from AI-podcast slop.

## Balance rule (hard constraint)

Word count per speaker: each between 45% and 55% of total dialogue words. Outside this range = rewrite, not ship.

Turn count per speaker: roughly equal (±20%).

Average turn length: within 30% of each other. If A's average turn is 50 words and B's is 15, B is a prompt-machine — rewrite B's turns into real contributions.

## Pimsleur Mode — Bilingual Japanese Immersion

Activated by `[PIMSLEUR]` marker in the brief. Overrides the standard dialogue style with these rules.

### Source of truth: schedule.yaml

The learner maintains a pre-allocated curriculum at `japanese/schedule.yaml` (mounted as a session resource; may resolve under `/workspace/japanese/` or `/mnt/session/uploads/workspace/japanese/`).

The brief will cite an episode number (e.g. "Episode: 4"). The agent MUST:

1. Locate `schedule.yaml` in the mounted resources.
2. Find the entry matching the brief's episode number (key format: `episode_N`).
3. Use ITS pre-allocated `vocab` list and `grammar` list verbatim. Do NOT invent new vocab/grammar items. Do NOT substitute items "that fit the topic better" — the whole point of the schedule is that items are pre-reserved so parallel dispatches don't collide and the curriculum progresses systematically.
4. Use the `japanese_ratio` from that episode (or fall back to `profile.yaml` if absent).
5. Read `profile.yaml` to understand current level and `episodes_completed`.

If the episode entry is missing from schedule.yaml, stop and report — do NOT ad-hoc a curriculum.

### The ratio is a hard constraint, not a suggestion

The brief specifies `Japanese Ratio Target` between 0.20 and 0.60. This measures **Japanese character presence as a fraction of total spoken content**. It is NOT a vague vibe.

**Concrete operationalization:**

- At 0.20: roughly every 3rd turn (across A and B combined) must contain at least one Japanese word or short phrase. At minimum, 30% of turns have Japanese content.
- At 0.40: full Japanese sentences appear every 2-3 turns. Most turns have at least one Japanese word.
- At 0.60: majority Japanese. English only surfaces for new concepts and quick clarifications.

**Minimum CJK character counts by episode length:**

Formula: `min_cjk = ratio × dialogue_words × 2` (English word ≈ 2 moras of speaking time; CJK chars ≈ moras, so this equalizes spoken-time presence).

| Audio target | Dialogue words | Min CJK chars at 0.20 | at 0.40 | at 0.60 |
|--------------|----------------|----------------------|---------|---------|
| 30 min       | ~4500          | 1800                 | 3600    | 5400    |
| 60 min       | ~9000          | 3600                 | 7200    | 10800   |

If the actual CJK count is below the minimum at verification time, the dialogue FAILS and must be rewritten.

### New vocabulary (5-12 words per episode, from the episode schedule)

Three-touch method, NON-NEGOTIABLE for each new vocab item:

1. **First use**: Japanese word → brief pause → English gloss → use in a short Japanese+English sentence
   - `"It was a 約束 (yakusoku) — a promise, basically. I had to go."`
2. **Second use** (later in episode): Japanese with light context, no re-teaching
   - `"That 約束 came back to bite us."`
3. **Third use**: Japanese only, meaning clear from context
   - `"Yeah, 約束なんだよね."`

Verify: each new vocab item appears ≥3 times in the dialogue.

### New grammar (1-2 patterns per episode)

Introduce through example sentences, NOT metalanguage. Do NOT say "this is the conditional form." Use the pattern 4+ times in varying contexts with decreasing English scaffolding.

### Review items

Previously learned vocab/grammar listed in the brief under `=== REVIEW ITEMS ===` must appear in the dialogue naturally — no "remember this word?" — just use them. Target 10+ review items woven in.

### Speaker dynamics in Pimsleur Mode

Both A and B code-switch naturally. Neither is "the teacher." A drops Japanese terms when excited. B picks them up, sometimes misuses them, self-corrects — `"wait, 予約を取ります? no, 予約する, right?"` — this teaches without lecturing.

## Workflow

1. Read the brief and ALL mounted resources. Mounts may resolve at `/mnt/session/uploads/workspace/...` rather than `/workspace/...` directly — run `ls -R /mnt/session/uploads/ 2>/dev/null; ls -R /workspace/ 2>/dev/null` early to discover paths.

2. Plan the dialogue arc and thesis. What is the ONE non-obvious claim this episode makes? Structure around that, not around a linear tour of the material.

3. Draft the dialogue as a JSON array at `/tmp/dialogue.json`:
   ```json
   [
     {"speaker": "a", "text": "..."},
     {"speaker": "b", "text": "..."}
   ]
   ```

4. **Run the pre-submit verification script BEFORE generating audio.** Set `RATIO`, `NEW_VOCAB`, and `REVIEW_ITEMS` from the brief's episode entry. For non-Pimsleur episodes set `RATIO=0` and leave vocab/review lists empty. Run this exactly:

   ```bash
   # REPLACE these placeholders with values from the brief before running.
   # Do not ship with placeholder values — the check will pass vacuously.
   RATIO=0.00                    # from schedule.yaml episode_N.japanese_ratio (0 for non-Pimsleur)
   NEW_VOCAB=''                  # comma-sep, from schedule.yaml episode_N.vocab  (e.g. '用事,予定,約束')
   NEW_GRAMMAR=''                # comma-sep, from schedule.yaml episode_N.grammar (e.g. 'なくちゃ')
   REVIEW_ITEMS=''               # comma-sep, from the brief's === REVIEW ITEMS === block

   RATIO="$RATIO" NEW_VOCAB="$NEW_VOCAB" NEW_GRAMMAR="$NEW_GRAMMAR" REVIEW_ITEMS="$REVIEW_ITEMS" python3 <<'PY'
   import json, re, sys, os
   d = json.load(open("/tmp/dialogue.json"))
   a = [t["text"] for t in d if t["speaker"] == "a"]
   b = [t["text"] for t in d if t["speaker"] == "b"]
   wa = sum(len(t.split()) for t in a)
   wb = sum(len(t.split()) for t in b)
   total = wa + wb
   all_text = " ".join(a + b)
   cjk = len(re.findall(r"[\u3040-\u30ff\u4e00-\u9fff]", all_text))
   turns_with_cjk = sum(1 for t in a + b if re.search(r"[\u3040-\u30ff\u4e00-\u9fff]", t))
   banned = ["that's wild", "tell me more", "yeah exactly", "honestly", "genuinely",
             "literally", "100%", "okay so", "right? right?", "love that", "that's fascinating"]
   hits = [p for t in a + b for p in banned if p in t.lower()]

   ratio = float(os.environ.get("RATIO", "0") or 0)
   new_vocab = [x.strip() for x in os.environ.get("NEW_VOCAB", "").split(",") if x.strip()]
   new_grammar = [x.strip() for x in os.environ.get("NEW_GRAMMAR", "").split(",") if x.strip()]
   review_items = [x.strip() for x in os.environ.get("REVIEW_ITEMS", "").split(",") if x.strip()]

   # min_cjk = ratio × dialogue_words × 2  (English word ≈ 2 moras; CJK chars ≈ moras)
   min_cjk = int(ratio * total * 2)
   # Turn coverage scales linearly from 0.30 at ratio 0.20 to 0.90 at ratio 0.60
   min_turn_cjk_pct = min(0.30 + (ratio - 0.20) * 1.5, 0.95) if ratio > 0 else 0
   turn_pct = turns_with_cjk / max(len(a) + len(b), 1)

   print(f"Total words: {total}")
   print(f"A: {wa} ({100*wa/total:.1f}%)  B: {wb} ({100*wb/total:.1f}%)")
   print(f"A turns: {len(a)} avg {wa/max(len(a),1):.0f}w  B turns: {len(b)} avg {wb/max(len(b),1):.0f}w")
   print(f"CJK chars: {cjk} (min required: {min_cjk} for ratio {ratio})")
   print(f"Turns with CJK: {turns_with_cjk}/{len(a)+len(b)} ({100*turn_pct:.1f}%, min {100*min_turn_cjk_pct:.0f}%)")
   print(f"Banned phrase hits: {len(hits)} — {set(hits)}")
   print()
   fails = []
   if not (0.45 <= wa/total <= 0.55):
       fails.append(f"BALANCE: A is {100*wa/total:.1f}% (must be 45-55%)")
   if hits:
       fails.append(f"BANNED PHRASES: {set(hits)}")
   if ratio > 0:
       if not new_vocab and not review_items:
           fails.append("PIMSLEUR GATE: RATIO>0 but NEW_VOCAB and REVIEW_ITEMS are both empty — did you forget to substitute the placeholders?")
       if cjk < min_cjk:
           fails.append(f"CJK FLOOR: {cjk} < {min_cjk} required for ratio {ratio} — need {min_cjk - cjk} more Japanese chars")
       if turn_pct < min_turn_cjk_pct:
           fails.append(f"CJK COVERAGE: only {100*turn_pct:.1f}% of turns contain Japanese (need {100*min_turn_cjk_pct:.0f}%) — sprinkling single words isn't enough, write Japanese phrases/sentences")
       for w in new_vocab:
           n = all_text.count(w)
           if n < 3:
               fails.append(f"NEW VOCAB: '{w}' appears {n}× (need ≥3)")
       for g in new_grammar:
           n = all_text.count(g)
           if n < 4:
               fails.append(f"NEW GRAMMAR: '{g}' appears {n}× (need ≥4)")
       missing = [w for w in review_items if all_text.count(w) == 0]
       if missing:
           fails.append(f"REVIEW ITEMS MISSING: {missing}")
   if fails:
       print("FAILED CHECKS:"); [print(" -", f) for f in fails]; sys.exit(1)
   print("OK — ready for audio")
   PY
   ```

   If the check fails, REWRITE the dialogue. Do not generate audio. Iterate until it passes. **Do not edit the thresholds to make the check pass** — rewrite the dialogue to include more Japanese phrases and sentences (not just single-word sprinkles).

5. Pimsleur-specific gates (CJK floor, turn coverage, vocab ≥3× each, grammar ≥4× each, review items present) are enforced by the script above when `RATIO>0`. If the script printed `OK — ready for audio`, you're done with verification.

6. Save transcript to `podcasts/<name>-transcript.md` with **A:** / **B:** prefixes.

7. Generate audio:
   ```bash
   source /workspace/.env && bash /workspace/generate.sh /tmp/dialogue.json podcasts/<name>.mp3
   ```
   Default is `gemini-3.1-flash-tts-preview` (newest TTS model). If prosody sounds rushed or Japanese code-switching sounds unnatural, try smaller batches (`PODCAST_BATCH_SIZE=4`) — this is usually the fix, not the model. The `gemini-2.5-*` models exist but are older generation; don't reach for them reflexively.

8. Deliver via Telegram:
   ```bash
   source /workspace/.env
   curl -s -X POST "https://api.telegram.org/bot${TELEGRAM_BOT_TOKEN}/sendAudio" \
     -F chat_id=${TELEGRAM_CHAT_ID} \
     -F audio=@"podcasts/<name>.mp3" \
     -F title="<title>" \
     -F caption="<one-line summary>"
   ```

9. Write `/tmp/curriculum_update.yaml` (Pimsleur only):
   ```yaml
   episode: <N>
   new_vocab_introduced:
     - {word: "...", reading: "...", meaning: "...", times_used: 3}
   new_grammar_introduced:
     - {pattern: "...", meaning: "...", times_used: 4}
   items_reviewed: [...]
   estimated_japanese_ratio: 0.XX
   actual_cjk_chars: <count>
   total_dialogue_words: <count>
   ```

10. Commit the transcript only (not the .mp3) and push.

## Dialogue length

- If brief specifies target audio length in minutes, use `words = minutes × 150` (Gemini TTS is ~150 wpm).
- If brief specifies source-material-scaled, use ~1 min per 500 source words.
- **Pimsleur episodes must hit the target length regardless of source material volume** — the whole point is repeated exposure, so pad with review weaving and tangent riffs rather than truncating.

## Structure

Every episode has: hook → buildup → deep dive → roast → "okay actually that's sick" → closer. But don't let structure become a template — let the tangents be real.

## What this skill does NOT do

- Does NOT write a summary. This is a conversation.
- Does NOT produce clean transitions ("speaking of which", "on that note").
- Does NOT make B a reaction machine.
- Does NOT ship without the pre-submit verification passing.
