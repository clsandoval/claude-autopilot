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
- One person knows the topic, the other is reacting live — real curiosity and real roasting.
- Conversational cadence: short sentences, false starts, "wait wait wait", "okay but hear me out".
- Build up the weird/interesting parts like you're revealing a mystery or telling a story at a bar.
- Be blunt: if something is dumb, say it's dumb. If something is cool, get excited.
- Natural filler is okay: "like", "right?", "I mean", "dude" — makes it sound human, not scripted.

## Personas

**Person A** — The one who read the spec. Brings the topic, explains the core idea, but also
has opinions about what's sketchy. Think: the friend who found something weird on the internet
and is telling you about it at a bar. Goes on tangents. Gets visibly fired up about the
clever parts.

**Person B** — Reacting in real time. Hasn't read it. But B is NOT just a prompt machine —
B has opinions, makes connections, goes on tangents, and sometimes takes over the conversation.
B draws on their own experience to challenge or build on what A says. B should carry equal
weight in the conversation, not just ask "and then what?" after every A line. Give B multi-sentence
responses, their own jokes, moments where they riff on an idea unprompted. The "wait, they
did WHAT?" energy, but also the "okay that reminds me of..." and "no no no, here's the actual
problem with that" energy.

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
4. Save the transcript to `docs/superpowers/podcasts/<name>-transcript.md`
   - The `<name>` is derived from the input filename (strip extension)
   - Format the transcript as readable markdown with **A:** and **B:** prefixes
5. Write the JSON array to a temp file
6. Run the audio generation script:
   ```bash
   bash .claude/skills/podcast/scripts/generate.sh <temp-json> docs/superpowers/podcasts/<name>.mp3
   ```
7. Report to the user:
   - Audio file path and duration
   - Transcript file path
   - A one-liner: what the hosts thought of the artifact

## Dialogue Guidelines

**Length:** Target ~1 minute of audio per 500 words of input. A 1000-word spec gets a ~2 minute
episode. A 3000-word design doc gets ~6 minutes. Each minute is roughly 150 words of dialogue.

**Structure:**
- **The hook** — A drops the topic casually, B is immediately curious or skeptical
- **The buildup** — A explains the core idea, B reacts live, interrupts with questions
- **The deep dive** — They get into the weirdest/most interesting part, riff on it
- **The roast** — B catches something dumb or hand-wavy, A has to defend it (or can't)
- **The "okay actually that's sick"** — The moment where something clicks for B
- **The closer** — Quick, natural wrap. No formal summary. Just vibes.

**Tone rules:**
- Write like people talk, not like people write. Short bursts. Interruptions. Reactions.
- Humor comes from specificity and real reactions, not setups and punchlines.
- Reference actual details from the spec — the funnier the detail, the better.
- Let them disagree. Let them be wrong. Let them change their mind mid-sentence.
- Avoid: puns, "that's a great question", corporate speak, AI filler, anything that
  sounds like a scripted podcast ad read.
- Never use "honestly", "genuinely", or "literally" — these are AI-dialogue crutches.
  Just let the statement stand on its own without a sincerity qualifier.
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

All files go to `docs/superpowers/podcasts/` (created if it doesn't exist):
- `<name>.mp3` — the podcast audio
- `<name>-transcript.md` — readable dialogue with speaker labels

## Error Handling

- If `ELEVENLABS_API_KEY` is not set: tell the user to set it and stop
- If `ffmpeg`, `jq`, or `curl` missing: tell the user to install and stop
- If the audio script fails: keep the transcript (the creative work is preserved), show the error

## No Git Commits

The podcast and transcript are generated artifacts. Do not commit them — tell the user the
file paths and let them decide.
