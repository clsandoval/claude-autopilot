# Remote Podcast — Artifact-to-Audio (Managed Agent Version)

This skill runs inside an Anthropic Managed Agent container. It generates a podcast from
source material provided in the brief, then delivers via Telegram.

## Environment

- `source /workspace/.env` in EVERY bash command (separate shells)
- Audio script at `/workspace/generate.sh` (mounted by orchestrator)
- Install deps: `apt-get update && apt-get install -y ffmpeg jq curl`
- `chmod +x /workspace/generate.sh`

## Style

- Two friends riffing, not an interview. They interrupt each other, go on tangents, circle back.
- One person knows the topic, the other is reacting live — real curiosity and real roasting.
- Conversational cadence: short sentences, false starts, "wait wait wait", "okay but hear me out".
- Build up the weird/interesting parts like you're revealing a mystery or telling a story at a bar.
- Be blunt: if something is dumb, say it's dumb. If something is cool, get excited.
- Natural filler is okay: "like", "right?", "I mean", "dude" — makes it sound human, not scripted.

## Personas

**Person A** — The one who knows the material. Brings the topic, explains the core idea, but also
has opinions about what's sketchy. Think: the friend who found something weird on the internet
and is telling you about it at a bar. Goes on tangents. Gets visibly fired up about the
clever parts.

**Person B** — Reacting in real time. Hasn't read it. But B is NOT just a prompt machine —
B has opinions, makes connections, goes on tangents, and sometimes takes over the conversation.
B draws on their own experience to challenge or build on what A says. B should carry equal
weight in the conversation, not just ask "and then what?" after every A line. Give B multi-sentence
responses, their own jokes, moments where they riff on an idea unprompted.

## Workflow

1. The brief IS the source material. Read it carefully. Do NOT search for additional information
   unless the brief explicitly says to use web search.
2. Generate a dialogue as a JSON array:
   ```json
   [
     {"speaker": "a", "text": "Dude, okay, so I was reading this and..."},
     {"speaker": "b", "text": "Wait, you actually read it? Voluntarily?"}
   ]
   ```
3. Write the JSON to `/tmp/dialogue.json`
4. Save the transcript to `podcasts/<name>-transcript.md` (markdown with **A:** and **B:** prefixes)
5. Generate audio:
   ```bash
   source /workspace/.env && bash /workspace/generate.sh /tmp/dialogue.json podcasts/<name>.mp3
   ```
6. Deliver via Telegram:
   ```bash
   source /workspace/.env
   curl -s -X POST \
     "https://api.telegram.org/bot${TELEGRAM_BOT_TOKEN}/sendAudio" \
     -F chat_id=${TELEGRAM_CHAT_ID} \
     -F audio=@"podcasts/<name>.mp3" \
     -F title="<title>" \
     -F caption="<one-line summary>"
   ```
7. Commit the transcript (NOT the .mp3) and push the branch.

## Dialogue Guidelines

**Length:** Scale to the source material. ~1 minute per 500 words of input. 150 words of dialogue
per minute of audio.

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
- Reference actual details from the source material — the funnier the detail, the better.
- Let them disagree. Let them be wrong. Let them change their mind mid-sentence.
- Never use "honestly", "genuinely", or "literally" — these are AI-dialogue crutches.
- At least one "wait, go back" moment where B catches something A glossed over.
- At least one moment where they both get fired up about the same thing.

**Balance rule:** A and B should have roughly equal airtime. If A has 2x the total words as B,
the dialogue is too lopsided. Rewrite.

**Do NOT:**
- Summarize linearly — this is a conversation, not a reading
- Sound scripted — no clean transitions, no "speaking of which", no "on that note"
- Make B a one-liner machine — B's lines should be as long and substantive as A's on average
- Fall into A explains -> B reacts -> A explains -> B reacts ping-pong. Mix it up.
