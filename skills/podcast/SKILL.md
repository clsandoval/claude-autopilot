---
name: podcast
description: |
  Turn any brainstorming artifact (spec, plan, design doc) into an engaging podcast-style
  audio conversation. Late-night talk show format with a witty host and enthusiastic guest.
  Triggers: "podcast", "make a podcast of", "turn this into a podcast", "podcast this spec"
---

# Podcast — Artifact-to-Audio

Convert a spec, plan, or design doc into a late-night talk show podcast. Two voices discuss
the artifact with humor, skepticism, and genuine exploration of the ideas.

## Invocation

```
podcast <filepath>
```

The argument is a path to a markdown or text file (spec, plan, design doc, etc.).

## Style

- Two friends riffing, not an interview. They interrupt each other, go on tangents, circle back.
- Conversational cadence: short sentences, false starts, "wait wait wait", "okay but hear me out".
- Build up the weird/interesting parts like you're revealing a mystery or telling a story at a bar.
- Be blunt: if something is dumb, say it's dumb.
- Natural filler is okay: "like", "right?", "I mean", "dude" — makes it sound human, not scripted.

## Default posture: pragmatic, pessimism-leaning, steelman-first

Both speakers default to **skeptical pragmatism**. Assume most claims in the artifact are overstated, under-specified, or won't survive contact with reality. The episode's job is to stress-test the material, not celebrate it.

This is NOT snark. The move is **steelman → critique**:

1. **Steelman first.** One speaker articulates the strongest honest version of each major claim — the version the author *wishes* they'd written. No critique lands before the steelman exists.
2. **Then critique.** Attack the steelmanned version. What load-bearing assumption breaks it? What's the cheapest experiment that would kill the idea? What prior art tried this and failed?
3. **End calibrated.** Not "this is great," not "this is doomed." A specific call: "works if X, falls over if Y, testable by Z."

Treat enthusiasm in the source material as a yellow flag, not a green light.

## Personas

**Neither speaker is the optimist or the hype person.** Both are pragmatist-skeptics who differ in *what kind* of skepticism.

**Person A** — One angle: e.g. the implementer who's read the spec and knows the gap between the README and the code. Has seen this pattern fail before.

**Person B** — A different angle: e.g. the market-skeptic, or the adjacent expert who knows a cheaper path achieves 80% of the value. B is NOT just a prompt machine. B has their own examples, their own prior art, their own disagreements. Multi-sentence responses, unprompted riffs, "no no no, here's the actual problem with that." Equal airtime and equal substance.

If either speaker catches themselves sounding like a booster, the other calls it out.

## Workflow

1. Read the artifact at the given filepath
2. Identify the key material:
   - The core thesis / what this thing actually does
   - The most interesting or novel decisions
   - The questionable or hand-wavy parts
   - The implications the author may not have considered
   - Anything that's unintentionally funny
3. Generate a dialogue as a JSON array. Each entry has `speaker` ("a" or "b") and `text`:
   ```json
   [
     {"speaker": "a", "text": "Dude, okay, so I was reading this spec and..."},
     {"speaker": "b", "text": "Wait, you actually read a spec? Voluntarily?"}
   ]
   ```
4. Determine the output directory:
   - Use `podcasts/` in the current working directory by default
   - Create the directory if it doesn't exist
5. Save the transcript to `podcasts/<name>-transcript.md`
   - The `<name>` is derived from the input filename (strip extension)
   - Format the transcript as readable markdown with **A:** and **B:** prefixes
6. Write the JSON array to a temp file (e.g. `/tmp/dialogue.json`)
6.5. **Run the pre-submit verification BEFORE audio generation. Hard-fail on any issue — rewrite the dialogue, do not edit the thresholds:**

   ```bash
   python3 <<'PY'
   import json, re, sys
   d = json.load(open("/tmp/dialogue.json"))
   a = [t["text"] for t in d if t["speaker"] == "a"]
   b = [t["text"] for t in d if t["speaker"] == "b"]
   wa = sum(len(t.split()) for t in a)
   wb = sum(len(t.split()) for t in b)
   total = wa + wb
   all_text = " ".join(a + b).lower()
   banned = ["that's wild", "tell me more", "yeah exactly", "honestly", "genuinely",
             "literally", "100%", "okay so", "right? right?", "love that", "that's fascinating"]
   sycophancy = ["good point", "great point", "fair point", "that's a good",
                 "you're right about", "you nailed it", "exactly what i",
                 "brilliant", "really cool", "so cool", "super cool",
                 "love how you", "love that you", "this is such",
                 "really well put", "couldn't have said", "nailed"]
   banned_hits = sorted({p for t in a + b for p in banned if p in t.lower()})
   syco_hits = [m for m in sycophancy if m in all_text]
   fails = []
   if not (0.45 <= wa/total <= 0.55):
       fails.append(f"BALANCE: A is {100*wa/total:.1f}% (must be 45-55%)")
   if banned_hits:
       fails.append(f"BANNED PHRASES: {banned_hits}")
   if len(syco_hits) > 1:
       fails.append(f"SYCOPHANCY: {len(syco_hits)} markers {syco_hits} — rewrite for pragmatic skepticism (see posture section)")
   print(f"Words A/B/Total: {wa}/{wb}/{total} — A={100*wa/total:.1f}%")
   print(f"Banned: {banned_hits}")
   print(f"Sycophancy: {syco_hits}")
   if fails:
       print("FAILED CHECKS:"); [print(" -", f) for f in fails]; sys.exit(1)
   print("OK — ready for audio")
   PY
   ```

7. Run the audio generation script:
   ```bash
   bash "${CLAUDE_PLUGIN_ROOT}/scripts/generate.sh" <temp-json> podcasts/<name>.mp3
   ```
8. Report to the user:
   - Audio file path and duration
   - Transcript file path
   - A one-liner: what the hosts thought of the artifact

## Dialogue Guidelines

**Length:** Target ~1 minute of audio per 500 words of input. A 1000-word spec gets a ~2 minute
episode. A 3000-word design doc gets ~6 minutes. Each minute is roughly 150 words of dialogue.

**Structure:**
- **The hook** — A drops the topic casually, B is immediately skeptical
- **The steelman** — one speaker articulates the strongest honest version of the material's core claim
- **The deep dive** — they get into the weirdest/most interesting part, riff on it
- **The what-breaks** — name specific failure modes, load-bearing assumptions, prior art that killed similar attempts
- **The calibrated closer** — "works if X, fails if Y, testable by Z". Not a verdict, not a vibes wrap. Do NOT end on celebration.

**Tone rules:**
- Write like people talk, not like people write. Short bursts. Interruptions. Reactions.
- Humor comes from specificity and real reactions, not setups and punchlines.
- Reference actual details from the spec — the funnier the detail, the better.
- Let them disagree. Let them be wrong. Let them change their mind mid-sentence.
- Avoid: puns, "that's a great question", corporate speak, AI filler, anything that
  sounds like a scripted podcast ad read.
- Banned AI-dialogue crutches: "honestly", "genuinely", "literally", "that's wild", "tell me more", "yeah exactly", "100%", "okay so", "right? right?", "love that", "that's fascinating". The pre-submit check (step 6.5) greps for these and fails the dialogue if any are present.
- Banned sycophancy markers (>1 hit = fail): "good point", "great point", "fair point", "that's a good", "you're right about", "you nailed it", "exactly what i", "brilliant", "really cool", "so cool", "super cool", "love how you", "love that you", "this is such", "really well put", "couldn't have said", "nailed".
- At least one "wait, go back" moment where B catches something A glossed over.
- At least one moment where they both get fired up about the same thing.

**Balance rule:** A and B should have roughly equal airtime. If A has spoken for 3+ lines
in a row, B needs to take over — not with a short reaction, but with a real thought. Count
the words: if A has 2x the total words as B, the dialogue is too lopsided. Rewrite.

**Do NOT:**
- Summarize the spec linearly — this is a conversation, not a reading
- Sound scripted — no clean transitions, no "speaking of which", no "on that note"
- Be mean-spirited — roasting is between friends, not from a critic
- Skip the interesting parts to cover everything — depth over breadth
- Generate dialogue longer than the content warrants — short specs get short episodes
- Use "Host:" and "Guest:" labels — use "A:" and "B:" to reinforce the peer dynamic
- Make B a one-liner machine — B's lines should be as long and substantive as A's on average
- Fall into A explains → B reacts → A explains → B reacts ping-pong. Mix it up.

## Output

All files go to `podcasts/` in the current working directory:
- `<name>.mp3` — the podcast audio
- `<name>-transcript.md` — readable dialogue with speaker labels

## Error Handling

- If `ELEVENLABS_API_KEY` is not set: tell the user to set it and stop
- If `ffmpeg`, `jq`, or `curl` missing: tell the user to install and stop
- If the audio script fails: keep the transcript (the creative work is preserved), show the error

## No Git Commits

The podcast and transcript are generated artifacts. Do not commit them — tell the user the
file paths and let them decide.
